from geosprite.stac.data.module import grid_to_tile
import argparse
import os


def cleanup(path: str):
    os.system(rf"find {path} -type f -name 'temp.tif' -delete")
    os.system(rf"find {path} -type f -name '*.vrt' -delete")
    os.system(rf"find {path} -type f -name '*.png.aux.xml' -delete")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--grid_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o1', '--color_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-o2', "--thumbnail_folder", help='destination Folder', type=str, required=True)
    parser.add_argument('-o3', '--tile_folder', help='destination Folder', type=str, required=True)
    parser.add_argument('-z', '--zoom', help='zoom levels', type=str, default="0-2")
    return parser.parse_args()


def main():
    args = parse_args()

    for production_name in os.listdir(args.grid_folder):
        production_path = os.path.join(args.grid_folder, production_name)
        color_file_path = os.path.join(production_path, "colorramp.txt")
        for year in os.listdir(production_path):
            src_path = os.path.join(production_path, year)
            if not os.path.isdir(src_path):
                continue
            grid_folder = os.path.join(args.grid_folder, production_name, year)
            color_folder = os.path.join(args.color_folder, production_name, year)
            thumbnail_folder = os.path.join(args.thumbnail_folder, production_name, year)
            tile_folder = os.path.join(args.tile_folder, production_name, year)

            print(f"{production_name} {year} data start:")
            grid_to_tile(grid_folder=grid_folder, color_folder=color_folder, color_file_path=color_file_path,
                         thumbnail_folder=thumbnail_folder, tile_folder=tile_folder, zoom=args.zoom)

            print(f"{production_name} {year} data end:")

    cleanup(args.grid_folder)
    cleanup(args.color_folder)
    cleanup(args.thumbnail_folder)
    cleanup(args.tile_folder)


if __name__ == "__main__":
    main()
