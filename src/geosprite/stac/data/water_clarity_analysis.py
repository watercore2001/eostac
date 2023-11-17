import argparse
import os
import itertools
from geosprite.stac.data.module import RasterImageProcessOptions, Calc


def parse_arg():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--water_clarity_folder', help='water distribution folder', type=str, required=True)
    parser.add_argument('-o1', '--change_folder', help='destination Folder', type=str, required=True)
    parser.add_argument("-o2", "--change_api_folder", type=str, required=True)
    parser.add_argument('-o3', '--statistics_folder', help='destination Folder', type=str, required=True)
    parser.add_argument("-o4", "--statistics_api_folder", type=str, required=True)
    return parser.parse_args()


def clarity_change():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_clarity_folder) if
             os.path.isdir(os.path.join(args.water_clarity_folder, year))]

    for pair in itertools.combinations(years, 2):
        src_path = [os.path.join(args.water_clarity_folder, year) for year in pair]
        dest_folder = os.path.join(args.change_folder, f"{pair[0]}-{pair[1]}")
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="B-A", output_type="Float32", hide_nodata=False)
        calc()


def clarity_change_api():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_clarity_folder) if
             os.path.isdir(os.path.join(args.water_clarity_folder, year))]

    for pair in itertools.combinations(years, 2):
        src_path = [os.path.join(args.water_clarity_folder, year) for year in pair]
        dest_folder = os.path.join(args.change_api_folder, f"{pair[0]}-{pair[1]}")
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="2*(B>=A)+(B<A)", output_type="Byte", hide_nodata=False)
        calc()
        calc.build_vrt("api.vrt")


def clarity_statistics():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_clarity_folder) if
             os.path.isdir(os.path.join(args.water_clarity_folder, year))]

    for year in years:
        src_path = [os.path.join(args.water_clarity_folder, year)]
        dest_folder = os.path.join(args.statistics_folder, year)
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="A*(A>0.5)", output_type="Float32", hide_nodata=False)
        calc()


def clarity_statistics_api():
    args = parse_arg()
    years = [year for year in os.listdir(args.water_clarity_folder) if
             os.path.isdir(os.path.join(args.water_clarity_folder, year))]

    for year in years:
        src_path = [os.path.join(args.water_clarity_folder, year)]
        dest_folder = os.path.join(args.statistics_api_folder, year)
        calc = Calc(
            RasterImageProcessOptions(src_path=src_path, dest_folder=dest_folder),
            calc="(A>=0.5)+(A>0)", output_type="Byte", hide_nodata=False)
        calc()
        calc.build_vrt("api.vrt")


def main():
    clarity_change()
    clarity_change_api()
    clarity_statistics()
    clarity_statistics_api()


if __name__ == "__main__":
    main()
