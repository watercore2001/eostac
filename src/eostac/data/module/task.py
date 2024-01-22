# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#

import dataclasses
import glob
import logging
import os
import shutil
import time
import uuid

from osgeo import gdal, ogr
from osgeo_utils import gdal2tiles, gdal_calc

from .utils import get_suffix_by_driver

logger = logging.getLogger(__name__)

SHP_DRIVER = ogr.GetDriverByName("ESRI Shapefile")
TIF_CREATE_OPTIONS = ["COMPRESS=DEFLATE", "INTERLEAVE=BAND", "BLOCKXSIZE=512", "BLOCKYSIZE=512"]


def time_it(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        func(*args, **kwargs)
        end = time.time()
        print(f'{func.__class__}:{end - start} seconds')

    return wrapper


@dataclasses.dataclass
class RasterImageProcessOptions:
    src_path: list[str]
    dest_folder: str
    recursive: bool = True
    input_suffix: str = "tif"
    driver_name: str = "GTiff"
    overwrite: bool = False
    rollback: bool = True


class RasterImageProcess:
    """
    Manage a list of raster files to do task.
    in one task, there are several src files and several dest file.
    for each task, do the same execution.
    """

    def __init__(
            self,
            options: RasterImageProcessOptions
    ):
        self.src_path = options.src_path
        self.dest_folder = options.dest_folder

        self.input_suffix = options.input_suffix
        self.output_suffix = get_suffix_by_driver(options.driver_name)
        self.recursive = options.recursive

        self.overwrite = options.overwrite
        self.rollback = options.rollback

        # put every file into a flatten task
        self.all_src = []
        self.all_dest = []

        # check dest path
        if not os.path.isdir(options.dest_folder):
            os.makedirs(options.dest_folder, exist_ok=True)

        # wait for split src and dest into several task
        self.tasks = []

    def split_task(self, **kwargs):
        """
        the default way to split task:
        for each file in src folder, create the same name file in destination folder
        """
        self.extract_src_paths()

        for path in self.all_src:
            # both src and dest maybe a list, so we use list
            src_in_task = [path]
            dest_file_name = os.path.splitext(os.path.basename(path))[0] + f".{self.output_suffix}"
            dest_in_task: list[str] = [os.path.join(self.dest_folder, dest_file_name)]
            self.tasks.append([src_in_task, dest_in_task, {}])

        self.flatten_dest_paths()

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        raise NotImplementedError

    def extract_src_paths(self):
        """
        extract all src files from src path
        """
        self.all_src = []
        for src_path in self.src_path:
            if os.path.isdir(src_path):
                if self.recursive:
                    src_path_match = os.path.join(src_path, "**", f"*.{self.input_suffix}")
                    self.all_src.extend(glob.iglob(src_path_match, recursive=True))
                else:
                    src_path_match = os.path.join(src_path, f"*.{self.input_suffix}")
                    self.all_src.extend(glob.iglob(src_path_match))
            elif os.path.isfile(src_path):
                self.all_src.append(src_path)
            else:
                raise ValueError(f"{src_path} should be a folder name or a list of file path names.")

    def flatten_dest_paths(self):
        """
        flatten all task destination into unnest list
        """
        self.all_dest = []
        for _, dest_task, _ in self.tasks:
            self.all_dest += dest_task

    @staticmethod
    def remove_existing_path(paths: list[str]) -> list[str]:
        real_test_in_task = []
        for path in paths:
            if os.path.isfile(path) and os.path.getsize(path) > 0:
                logger.info(f"Destination file exists : {path}")
            else:
                real_test_in_task.append(path)
        return real_test_in_task

    @staticmethod
    def remove_existing_file(paths: list[str]):
        for path in paths:
            if os.path.isfile(path):
                os.remove(path)

    @time_it
    def __call__(self, **kwargs):
        all_success = True

        for src_in_task, dest_in_task, task_args in self.tasks:
            if not self.overwrite:
                dest_in_task = self.remove_existing_path(dest_in_task)
                if len(dest_in_task) == 0:
                    continue

            success = self.execute(src_in_task, dest_in_task, **task_args)

            if success is False:
                all_success = False

                logger.info(
                    f"Execute module '{self.__class__.__name__}' failed: "
                    f"source pathname: {src_in_task}, destination pathname: {dest_in_task}")

                if self.rollback:
                    self.remove_existing_file(dest_in_task)
                    logger.info(f"Execute failed and rollback is performed. Remove file {dest_in_task}.")
        return all_success

    def build_vrt(self, filename: str = None) -> str:
        if filename is None:
            filename = f"{str(uuid.uuid4())}.vrt"
        vrt_file = os.path.join(self.dest_folder, filename)
        gdal.BuildVRT(vrt_file, self.all_dest)
        return vrt_file


class ReProjection(RasterImageProcess):

    def __init__(
            self,
            options: RasterImageProcessOptions,
            output_epsg: int = 4326,
    ):
        super().__init__(options)
        self.split_task()
        self.output_epsg = output_epsg
        self.options = {"dstSRS": f"epsg:{output_epsg}", "creationOptions": TIF_CREATE_OPTIONS}

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        ds = gdal.Open(src_in_task[0])
        input_epsg = int(ds.GetSpatialRef().GetAttrValue("AUTHORITY", 1))
        if input_epsg == self.output_epsg:
            return shutil.copy(src_in_task[0], dest_in_task[0])

        return gdal.Warp(dest_in_task[0], src_in_task[0], **self.options)


class WGS84Grid(RasterImageProcess):
    def __init__(
            self,
            options: RasterImageProcessOptions,
            grid_shp_path: str,
            name_format: str,
    ):
        super().__init__(options)
        self.name_format = name_format
        self.split_task(grid_shp_path)
        self.options = {"format": options.driver_name, "creationOptions": TIF_CREATE_OPTIONS,
                        "stats": True}

    def dest_filename(self, lng_centre: float, lat_centre: float):
        lng_min = lng_centre - lng_centre % 5
        lat_min = lat_centre - lat_centre % 5

        lng_str = f"E{lng_min:.0f}" if lng_min >= 0 else f"W{-lng_min:.0f}"
        lat_str = f"N{lat_min:.0f}" if lat_min >= 0 else f"S{-lat_min:.0f}"

        return self.name_format.format(lng_str, lat_str) + "." + self.output_suffix

    def split_task(self, grid_shp_path: str):
        input_ds = SHP_DRIVER.Open(grid_shp_path, 0)
        input_layer = input_ds.GetLayer()
        for feature in input_layer:
            geometry = feature.geometry()
            # grid code
            centroid = geometry.Centroid()
            dest_file = os.path.join(self.dest_folder, self.dest_filename(centroid.GetX(), centroid.GetY()))
            # grid extent
            lng_min, lng_max, lat_min, lat_max = geometry.GetEnvelope()
            extent = [lng_min, lat_max, lng_max, lat_min]
            self.tasks.append([self.src_path, [dest_file], {"projWin": extent}])

        self.flatten_dest_paths()

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        kwargs.update(self.options)
        return gdal.Translate(dest_in_task[0], src_in_task[0], **kwargs)


class ColorRamp(RasterImageProcess):
    def __init__(self,
                 options: RasterImageProcessOptions,
                 color_file_path: str,
                 ):
        super().__init__(options)
        self.split_task()
        self.scale_params = [self.get_scale_params(color_file_path)]
        self.color_table = self.get_color_ramp(color_file_path)
        # 1. convert to byte type
        self.options1 = {"creationOptions": TIF_CREATE_OPTIONS, "outputType": gdal.gdalconst.GDT_Byte,
                         "scaleParams": self.scale_params}
        # 2. add rgba
        self.options2 = {"creationOptions": TIF_CREATE_OPTIONS, "rgbExpand": "rgba"}

    @staticmethod
    def get_scale_params(color_file_path: str):
        start_scale = None
        end_scale = None
        print(color_file_path)
        with open(color_file_path) as f:
            for line in f:
                print(line)
                line = line.strip()
                if not line[0].isdigit():
                    continue
                if start_scale is None:
                    start_scale = line.split(",")[0]
                end_scale = line.split(",")[0]
        return float(start_scale), float(end_scale)

    def get_color_ramp(self, color_file_path: str):
        color_table = gdal.ColorTable()
        start_line = None
        end_line = None
        with open(color_file_path) as f:
            for line in f:
                if not line[0].isdigit():
                    continue
                if start_line is None:
                    start_line = line
                    continue
                if end_line is None:
                    end_line = line
                    color_table.CreateColorRamp(*self.match_line(start_line), *self.match_line(end_line))
                    continue
                start_line = end_line
                end_line = line
                color_table.CreateColorRamp(*self.match_line(start_line), *self.match_line(end_line))

        return color_table

    def match_line(self, line: str):
        strs = line.split(",")
        scale_size = self.scale_params[0][1] - self.scale_params[0][0]
        value = int(float(strs[0]) / scale_size * 255)
        rgba = tuple(map(int, strs[1:5]))
        return value, rgba

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        temp_file = os.path.join(self.dest_folder, r"temp.tif")
        gdal.Translate(temp_file, src_in_task[0], **self.options1)
        ds = gdal.Open(temp_file, gdal.gdalconst.GA_Update)
        band = ds.GetRasterBand(1)
        band.SetRasterColorTable(self.color_table)
        band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)
        del ds
        result = gdal.Translate(dest_in_task[0], temp_file, **self.options2)
        os.remove(temp_file)
        return result


class Thumbnail(RasterImageProcess):
    def __init__(self,
                 options: RasterImageProcessOptions,
                 width_percent: float,
                 height_percent: float):
        super().__init__(options)
        self.split_task()
        self.options = {"format": options.driver_name,
                        "widthPct": width_percent, "heightPct": height_percent}

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        kwargs.update(self.options)
        result = gdal.Translate(dest_in_task[0], src_in_task[0], **kwargs)
        return result


class XYZTiles(RasterImageProcess):
    def __init__(
            self,
            options: RasterImageProcessOptions,
            zoom: str,
            processes: int = 4,
            resampling: str = "near",
            web_viewer: str = "all",
    ):
        super().__init__(options)
        self.split_task()
        self.options = ["--xyz", "--exclude", "--resume", f"--zoom={zoom}", f"--processes={processes}",
                        f"--resampling={resampling}", f"--webviewer={web_viewer}"]

    def split_task(self, **kwargs):
        self.tasks.append([self.src_path, [self.dest_folder], {}])

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        options = self.options + [src_in_task[0], dest_in_task[0]]
        return gdal2tiles.main(options) == 0


class Calc(RasterImageProcess):
    def __init__(self,
                 options: RasterImageProcessOptions,
                 calc: str,
                 output_type: str = "Byte",
                 hide_nodata: bool = True,
                 nodata: int = 0):
        super().__init__(options)
        self.split_task()
        self.options = [f"--calc={calc}", "--quiet", f"--type={output_type}", "--overwrite"]
        if hide_nodata:
            self.options.append("--hideNoData")
        if nodata is not None:
            self.options.append(f"--NoDataValue={nodata}")

    def split_task(self, **kwargs):
        self.all_src = []
        self.all_dest = []
        first_input_folder = self.src_path[0]
        path_match = os.path.join(first_input_folder, f"*.{self.input_suffix}")
        for first_input_file in glob.iglob(path_match):
            task = [[], [], {}]
            basename = os.path.basename(first_input_file)
            prefix = basename.rsplit("_", 1)[0]
            task[0] = self.find_all_files_in_src_folders(prefix)

            dest_file = os.path.join(self.dest_folder, f"{prefix}.tif")
            task[1].append(dest_file)
            self.all_src.extend(task[0])
            self.all_dest.extend(task[1])
            self.tasks.append(task)

    def find_all_files_in_src_folders(self, prefix: str):
        input_files_in_one_task = []
        for folder in self.src_path:
            path_match = os.path.join(folder, f"{prefix}*.{self.input_suffix}")
            for file in glob.iglob(path_match):
                input_files_in_one_task.append(file)

        return input_files_in_one_task

    def execute(self, src_in_task: list[str], dest_in_task: list[str], **kwargs) -> bool:
        # in argv, to represent space, should use two item in list
        options = [" "]  # the first should be a placeholder
        for i, input_file in enumerate(src_in_task):
            options.append(f"-{chr(ord('A') + i)}")
            options.append(input_file)
        options.append(f"--outfile={dest_in_task[0]}")
        for create_option in TIF_CREATE_OPTIONS:
            options.append(f"--creation-option={create_option}")
        options.extend(self.options)
        return gdal_calc.main(options) == 0
