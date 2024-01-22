from eostac.data.module.xyz import raw_to_grid
import argparse
import os


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--raw_folder', type=str, required=True)
    parser.add_argument('-o1', '--wgs84_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o2', "--grid_folder", help='destination Folder', type=str, required=True)
    parser.add_argument('-g', "--grid_shp_path", help="wgs84 grids", type=str, required=True)
    parser.add_argument('-f', "--name_format", help="grid name format with four place holder", type=str,
                        required=True, default="aircas_{}_yearly_{}_{}_{}")
    return parser.parse_args()


def main():
    args = parse_args()

    for production_name in os.listdir(args.raw_folder):
        production_path = os.path.join(args.raw_folder, production_name)
        for year in os.listdir(production_path):
            raw_folder = os.path.join(production_path, year)
            if not os.path.isdir(raw_folder):
                continue
            wgs84_folder = os.path.join(args.wgs84_folder, production_name, year)
            grid_folder = os.path.join(args.grid_folder, production_name, year)
            name_format = args.name_format.format(production_name, "{}", "{}", year)
            print(f"{production_name} {year} data start:")
            raw_to_grid(raw_folder=raw_folder, wgs84_folder=wgs84_folder, grid_folder=grid_folder,
                        grid_shp_path=args.grid_shp_path, name_format=name_format)

            print(f"{production_name} {year} data end:")


if __name__ == "__main__":
    main()
