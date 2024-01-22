# Copyright (c) GeoSprite. All rights reserved.
#
# Author: Jia Song
#
import argparse
import os

from eostac.data.module import RasterImageProcessOptions, ReProjection, WGS84Grid, Thumbnail, \
    ColorRamp, XYZTiles


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--raw_folder', help='Source Path', nargs="+", type=str, required=True)
    parser.add_argument('-o1', '--wgs84_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o2', '--grid_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o3', '--color_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o4', "--thumbnail_folder", help='destination Folder', type=str, required=True)
    parser.add_argument('-o5', '--tile_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-g', "--grid_shp_path", help="wgs84 grids", type=str, required=True)
    parser.add_argument('-f', "--name_format", help="grid name format with two place holder", type=str, required=True)
    parser.add_argument('-c', "--color_file_path", help="color ramp file in qgis", type=str, required=True)
    parser.add_argument('-z', '--zoom', help='zoom levels', type=str, default="0-2")

    return parser.parse_args()


def raw_to_grid(raw_folder: str, wgs84_folder: str, grid_folder: str, grid_shp_path: str, name_format: str):
    """
    Args:
        raw_folder: raw data foldr
        wgs84_folder: wgs84 data folder
        grid_folder: grid data folder
        grid_shp_path: grid shapefile path
        name_format: grid name format
    """
    # re projection
    wgs84_epsg = 4326
    projection = ReProjection(RasterImageProcessOptions(src_path=[raw_folder], dest_folder=wgs84_folder),
                              output_epsg=wgs84_epsg)
    if projection() is False or len(projection.all_dest) == 0:
        return

    # WGS84 grids
    projection_vrt_path = projection.build_vrt()
    wgs84_grid = WGS84Grid(RasterImageProcessOptions(src_path=[projection_vrt_path], dest_folder=grid_folder),
                           grid_shp_path=grid_shp_path, name_format=name_format)
    if wgs84_grid() is False or len(wgs84_grid.all_dest) == 0:
        os.remove(projection_vrt_path)
        return
    os.remove(projection_vrt_path)


def grid_to_tile(grid_folder: str, color_folder: str, color_file_path: str, thumbnail_folder: str, tile_folder: str,
                 zoom: str):
    # color map
    color_ramp = ColorRamp(RasterImageProcessOptions(src_path=[grid_folder], dest_folder=color_folder),
                           color_file_path=color_file_path)
    if color_ramp() is False or len(color_ramp.all_dest) == 0:
        return

    # thumbnail of each grid
    each_thumbnail = Thumbnail(
        RasterImageProcessOptions(src_path=[color_folder], dest_folder=thumbnail_folder, driver_name="PNG"),
        width_percent=5, height_percent=5)
    if each_thumbnail() is False or len(each_thumbnail.all_dest) == 0:
        return

    # thumbnail of all grid
    color_vrt_filename = "all_thumbnail.vrt"
    color_vrt_path = color_ramp.build_vrt(filename=color_vrt_filename)
    all_thumbnail = Thumbnail(
        RasterImageProcessOptions(src_path=[color_vrt_path], dest_folder=thumbnail_folder, driver_name="PNG"),
        width_percent=1, height_percent=1)
    if all_thumbnail() is False or len(all_thumbnail.all_dest) == 0:
        return

    # XYZ google Tiles
    color_vrt_path = color_ramp.build_vrt()
    xyz_tiles = XYZTiles(RasterImageProcessOptions(src_path=[color_vrt_path], dest_folder=tile_folder), zoom=zoom)
    if xyz_tiles() is False or len(xyz_tiles.all_dest) == 0:
        os.remove(color_vrt_path)
        return
    os.remove(color_vrt_path)




def main():
    args = parse_args()

    raw_to_grid(raw_folder=args.raw_folder,
                wgs84_folder=args.wgs84_folder,
                grid_folder=args.grid_folder,
                grid_shp_path=args.grid_shp_path,
                name_format=args.name_format)
    grid_to_tile(grid_folder=args.grid_folder,
                 color_folder=args.color_folder,
                 color_file_path=args.color_file_path,
                 thumbnail_folder=args.thumbnail_folder,
                 tile_folder=args.tile_folder,
                 zoom=args.zoom)


if __name__ == '__main__':
    '''
    Example:
    xyz.py 
        -i /home/watercore/data/hkh/water_clarity/2000
        -o1 /home/watercore/data/hkh/temp_data/water_clarity/2000
        -o2 /home/watercore/data/hkh/temp_data/water_clarity/2000
        -o3 /home/watercore/data/hkh/temp_data/water_clarity/2000
        -o4 /home/watercore/data/hkh/temp_data/water_clarity/2000
        -g /home/watercore/data/hkh/extent/grid.shp 
        -f aircas_water_distribution_yearly_{}_{}_2000
        -c /home/watercore/data/hkh/water_clarity/water_clarity.txt
        -z 0-1 -p 4
    '''
    main()
