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
    if item_id.startswith("aircas_land_cover_yearly"):
        return f"Land cover of HKH region for {part_tile}"
    if item_id.startswith("aircas_land_utilization_intensity_yearly"):
        return f"Land utilization intensity of HKH region for {part_tile}"
    if item_id.startswith("aircas_labor_output_yearly"):
        return f"Labor output of HKH region for {part_tile}"
    if item_id.startswith("aircas_bio_mass_yearly"):
        return f"Bio mass of HKH region for {part_tile}"
    raise Exception


def add_asset_to_item(item: pystac.Item, thumbnail_url: str, data_url: str) -> None:
    thumbnail_asset = pystac.Asset(href=thumbnail_url, media_type=pystac.MediaType.PNG)
    item.add_asset(key="thumbnail", asset=thumbnail_asset)
    data_asset = pystac.Asset(href=data_url, media_type=pystac.MediaType.GEOTIFF)
    item.add_asset(key="data", asset=data_asset)


def make_items(collection_id: str, root_folder: str, collection_folder: str) -> list[pystac.Item]:
    items = []

    for year in os.listdir(os.path.join(collection_folder, "grid")):
        year_folder = os.path.join(collection_folder, "grid", year)
        if not os.path.isdir(year_folder):
            continue
        date_time = datetime.datetime(year=int(year), month=6, day=1)

        for image_filename in os.listdir(year_folder):
            if not image_filename.endswith(".tif"):
                continue
            basename = os.path.splitext(os.path.basename(image_filename))[0]
            image_filepath = os.path.join(year_folder, image_filename)
            bbox, geom = get_bbox_and_geom(image_filepath)

            properties_dict = {
                "extent": rf"{bbox[1]:.3f}°N~{bbox[3]:.3f}°N,{bbox[0]:.3f}°E~{bbox[2]:.3f}°E",
                "year": year,
                "title": get_item_title(basename)
            }

            item = pystac.Item(id=basename, collection=collection_id, bbox=bbox, geometry=geom,
                               datetime=date_time, properties=properties_dict)
            # add asset
            thumbnail_filename = basename + ".png"
            thumbnail_filepath = f"{collection_folder}/thumbnail/{year}/{thumbnail_filename}"

            # image_prefix: "grid_data/water_distribution/2000/blabla.tif"
            image_prefix = os.path.relpath(image_filepath, root_folder)
            thumbnail_prefix = os.path.relpath(thumbnail_filepath, root_folder)
            add_asset_to_item(item, thumbnail_prefix, image_prefix)
            # add item to items
            items.append(item)
    return items


def make_collection(stac_client: Client, nginx_socket: str, root_folder: str, collection_folder: str):
    # 0.read metadata json file
    metadata_filepath = os.path.join(collection_folder, "grid", "metadata.json")
    with open(metadata_filepath) as file:
        metadata = json.load(file)
    collection_id = metadata["collection_id"]
    title = metadata["title"]
    description = metadata["description"]
    info = metadata["summaries"]

    # 1.extent
    items = make_items(collection_id, root_folder, collection_folder)
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
    collection_thumbnail = os.path.join(collection_folder, "thumbnail", "all_thumbnail.png")
    collection_thumbnail_prefix = os.path.relpath(collection_thumbnail, root_folder)

    legend = os.path.join(collection_folder, "grid", "legend.png")
    legend_prefix = os.path.relpath(legend, root_folder)

    summaries_dict = {"abs_path": nginx_socket,
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


def make_catalog(root: str, stac_client: Client, nginx_socket: str):
    for catalog in os.listdir(root):
        catalog_folder = os.path.join(root, catalog)

        for collection in os.listdir(catalog_folder):
            collection_folder = os.path.join(catalog_folder, collection)
            make_collection(stac_client, nginx_socket, root, collection_folder)


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument("-i", "--input_folder", type=str, default="/mnt/disk/geodata/hkh/data/stac/")
    parser.add_argument("-a", "--stac_api_socket", type=str, default="http://10.168.162.112:23456/")
    parser.add_argument("-n", "--nginx_socket", type=str, default="http://10.168.162.112:28001/")

    return parser.parse_args()


def main():
    args = parse_args()
    stac_client = Client(domain_url=args.stac_api_socket)

    make_catalog(root=args.input_folder, stac_client=stac_client, nginx_socket=args.nginx_socket)


if __name__ == "__main__":
    main()

