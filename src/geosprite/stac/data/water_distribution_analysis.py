import argparse
import os
import itertools
from geosprite.stac.data.module import RasterImageProcessOptions, Calc
import shutil
from osgeo import gdal


def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--water_distribution_folder', help='water distribution folder', type=str, required=True)
    parser.add_argument('-o1', '--change_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o2', '--statistics_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o3', '--api_folder', help='destination Folder', type=str, required=True)
    return parser.parse_args()


def distribution_change():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_distribution_folder) if
             os.path.isdir(os.path.join(args.water_distribution_folder, year))]

    for pair in itertools.combinations(years, 2):
        src_path = [os.path.join(args.water_distribution_folder, year) for year in pair]
        dest_folder = os.path.join(args.change_folder, f"{pair[0]}-{pair[1]}")
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder, overwrite=False),
            calc="A+2*B", output_type="Byte", hide_nodata=True)
        calc()


def distribution_statistics():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_distribution_folder) if
             os.path.isdir(os.path.join(args.water_distribution_folder, year))]

    for year in years:
        src_path = os.path.join(args.water_distribution_folder, year)
        dest_folder = os.path.join(args.statistics_folder, year)
        os.makedirs(dest_folder, exist_ok=True)
        for file in os.listdir(src_path):
            src_file_path = os.path.join(src_path, file)
            dest_file_path = os.path.join(dest_folder, file)
            shutil.copy(src_file_path, dest_file_path)

    for pair in itertools.combinations(years, 2):
        src_path = [os.path.join(args.water_distribution_folder, year) for year in pair]
        dest_folder = os.path.join(args.statistics_folder, f"{pair[0]}-{pair[1]}")
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="A+B", output_type="Byte", hide_nodata=True)
        calc()

    for pair in itertools.combinations(years, 3):
        src_path = [os.path.join(args.water_distribution_folder, year) for year in pair]
        dest_folder = os.path.join(args.statistics_folder, f"{pair[0]}-{pair[1]}-{pair[2]}")
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="A+B+C", output_type="Byte", hide_nodata=True)
        calc()


def distribution_api():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_distribution_folder) if
             os.path.isdir(os.path.join(args.water_distribution_folder, year))]

    for year in years:
        src_path = os.path.join(args.water_distribution_folder, year)
        dest_folder = os.path.join(args.api_folder, year)
        os.makedirs(dest_folder, exist_ok=True)
        dest_files = []
        for file in os.listdir(src_path):
            src_file_path = os.path.join(src_path, file)
            dest_file_path = os.path.join(dest_folder, file)
            shutil.copy(src_file_path, dest_file_path)
            dest_files.append(dest_file_path)
        gdal.BuildVRT(os.path.join(dest_folder, "api.vrt"), dest_files)


def main():
    distribution_change()
    distribution_statistics()
    distribution_api()


if __name__ == "__main__":
    main()
