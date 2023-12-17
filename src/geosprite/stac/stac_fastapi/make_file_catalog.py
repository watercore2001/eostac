import argparse
import dataclasses
import datetime
import json
import os.path
import re

import pystac
import rasterio
import requests
from shapely import geometry


@dataclasses.dataclass
class Client:
    domain_url: str

    def get(self, path: str):
        response = requests.get(os.path.join(self.domain_url, path))
        # assert response.status_code == 200, response.status_code
        return response.json()

    def post(self, path: str, json_data: str):
        response = requests.post(os.path.join(self.domain_url, path), data=json_data)
        # assert response.status_code == 200, response.status_code
        return response.json()

    def put(self, path: str, json_data: str):
        response = requests.put(os.path.join(self.domain_url, path), data=json_data)
        # assert response.status_code == 200
        return response.json()

    def delete(self, path: str):
        response = requests.delete(os.path.join(self.domain_url, path))
        # assert response.status_code == 200
        return response.json()


def get_bbox_and_geom(image_path: str):
    print(image_path)
    with rasterio.open(image_path) as ds:
        bounds = ds.bounds
        bbox = [bounds.left, bounds.bottom, bounds.right, bounds.top]
        geom = geometry.Polygon(
            [
                [bounds.left, bounds.bottom],
                [bounds.left, bounds.top],
                [bounds.right, bounds.top],
                [bounds.right, bounds.bottom],
            ]
        )

        return bbox, geometry.mapping(geom)


def get_item_title(item_id: str) -> str:
    match_min_lat = re.search(r'N(\d+)', item_id)
    min_lat = int(match_min_lat.group(1))

    match_min_lng = re.search(r'E(\d+)', item_id)
    min_lng = int(match_min_lng.group(1))

    year = item_id.split("_")[-1]
    part_tile = f"{year} ({min_lng}-{min_lng + 5}E {min_lat}-{min_lat + 5}N)"

    if item_id.startswith("aircas_water_distribution_yearly"):
        return f"Water body distribution of HKH region for {part_tile}"
    if item_id.startswith("aircas_water_clarity_yearly"):
        return f"Water clarity of HKH region for {part_tile}"
    if item_id.startswith("aircas_water_distribution_10m_yearly"):
        return f"Water body distribution 10m of HKH region for {part_tile}"
    if item_id.startswith("aircas_forest_grass_yearly"):
        return f"Forest grass distribution of HKH region for {part_tile}"
    if item_id.startswith("aircas_fractional_vegetation_coverage_yearly"):
        return f"Fractional vegetation coverage of HKH region for {part_tile}"


def add_asset_to_item(item: pystac.Item, thumbnail_url: str, data_url: str) -> None:
    thumbnail_asset = pystac.Asset(href=thumbnail_url, media_type=pystac.MediaType.PNG)
    item.add_asset(key="thumbnail", asset=thumbnail_asset)
    data_asset = pystac.Asset(href=data_url, media_type=pystac.MediaType.GEOTIFF)
    item.add_asset(key="data", asset=data_asset)


def make_items(collection_id: str, input_folder:str, production_name:str, years:list) -> list[pystac.Item]:
    items = []
    for year in years:
        date_time = datetime.datetime(year=int(year), month=6, day=1)
        year_folder = os.path.join(input_folder, "grid_data", production_name, str(year))
        for image_path in os.listdir(year_folder):

            basename = os.path.splitext(os.path.basename(image_path))[0]
            bbox, geom = get_bbox_and_geom(image_path)

            properties_dict = {
                "extent": rf"{bbox[1]:.3f}°N~{bbox[3]:.3f}°N,{bbox[0]:.3f}°E~{bbox[2]:.3f}°E",
                "year": year,
                "title": get_item_title(basename)
            }
            item = pystac.Item(id=basename, collection=collection_id, bbox=bbox, geometry=geom,
                               datetime=date_time, properties=properties_dict)
            # add asset
            thumbnail_filename = basename + ".png"
            thumbnail_prefix = f"thumbnail_data/{production_name}/{year}/{thumbnail_filename}"
            # image_prefix: "grid_data/water_distribution/2000/blabla.tif"
            image_prefix = os.path.relpath(image_path, input_folder)
            add_asset_to_item(item, thumbnail_prefix, image_prefix)
            # add item to items
            items.append(item)
    return items


def make_collection(stac_client: Client, input_folder: str, production_name: str, years: list):
    # 0.read metadata json file
    metadata_filepath = os.path.join(input_folder, f"grid_data/{production_name}/metadata.json")
    with open(metadata_filepath) as file:
        metadata = json.load(file)
    collection_id = metadata["collection_id"]
    title = metadata["title"]
    description = metadata["description"]
    info = metadata["summaries"]

    # 1.extent
    items = make_items(collection_id, input_folder, production_name, years)
    # spatial extent
    geoms = set(map(lambda i: geometry.shape(i.geometry).envelope, items))
    collection_bbox = geometry.MultiPolygon(geoms).bounds
    spatial_extent = pystac.SpatialExtent(bboxes=[collection_bbox])
    # temporal extent
    years = sorted(set(map(lambda i: i.datetime.year, items)))
    intervals = []
    for year in years:
        start_datatime = datetime.datetime(year, 1, 1, 0, 0, 0, 0)
        end_datetime = datetime.datetime(year, 12, 31, 23, 59, 59, 999999)
        intervals.append([start_datatime, end_datetime])
    overall_interval = [intervals[0][0], intervals[-1][-1]]
    intervals.insert(0, overall_interval)
    temporal_extent = pystac.TemporalExtent(intervals=intervals)

    extent = pystac.Extent(spatial=spatial_extent, temporal=temporal_extent)

    # 2.summaries
    # tile_urls = []
    # for year in years:
    #     tile_url = os.path.join(collection_tile_url, f"{year}/")
    #     year_tile = {"year": str(year), "collection_id": collection_id, "url": tile_url}
    #     tile_urls.append(year_tile)

    collection_thumbnail_prefix = f"thumbnail_data/{production_name}/all_thumbnail.png"
    legend_prefix = f"grid_data/{production_name}/legend.png"

    summaries_dict = {"abs_path": input_folder,
                      "thumbnail_rel_path": collection_thumbnail_prefix,
                      "legend_rel_path": legend_prefix,
                      "info": info}

    summaries = pystac.Summaries(summaries_dict)

    # 4.create collection
    collection = pystac.Collection(id=metadata["collection_id"], title=title,
                                   description=description, extent=extent, summaries=summaries)

    # del
    # for item in items:
    #     stac_client.delete(f"collections/{collection_id}/items/{item.id}")
    # stac_client.delete(f"collections/{collection_id}")

    # post
    stac_client.post(f"collections/", json.dumps(collection.to_dict()))
    for item in items:
        stac_client.post(f"collections/{collection_id}/items/", json.dumps(item.to_dict()))


def make_catalog(input_folder: str, stac_client: Client, production_names:dict):
    for production_name, years in production_names.items():
        make_collection(stac_client, input_folder, production_name, years)

def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input_folder", type=str)
    parser.add_argument("-a", "--stac_api_socket", type=str, default="http://127.0.0.1:23456/")

    # parser.add_argument("-i", "--grid_data_folder", type=str, default="/home/watercore/data/hkh/grid_data")
    # parser.add_argument("-a", "--stac_api_socket", type=str, default="127.0.0.1:23456")
    # parser.add_argument("-n", "--nginx_socket", type=str, default="127.0.0.1:28001")

    return parser.parse_args()


def main():
    production_names = {"forest_grass": [2000, 2010, 2020], "fractional_vegetation_coverage": [2000, 2010, 2020],
                        "water_clarity": [2000, 2010, 2020], "water_distribution": [2000, 2010, 2020],
                        "water_distribution_10m": [2016, 2017, 2018, 2019, 2020, 2021, 2022]}

    args = parse_args()
    stac_client = Client(domain_url=args.stac_api_socket)

    make_catalog(input_folder=args.input_folder, stac_client=stac_client, production_names=production_names)


if __name__ == "__main__":
    main()

