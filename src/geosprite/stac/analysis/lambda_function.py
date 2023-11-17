import json
import rasterio
from shapely.geometry import shape
from rasterio import mask as msk
import time
import numpy as np

def lambda_handler(event, context):
    geojson: dict = event["geojson"]
    product_name: str = event["product_name"]
    year: str = event["year"]
    statistic_values: list[int] = event["statistic_values"]

    shapely_geoms = [shape(feature["geometry"]) for feature in geojson["features"]]
    vrt_file = f"s3://geosprite-api-data/api_data/{product_name}/{year}/api.vrt"

    with rasterio.open(vrt_file) as src:
        start_time = time.time()
        crop_image, _ = msk.mask(src, shapely_geoms, crop=True)
        output_dict = {value: np.count_nonzero(crop_image == value) for value in statistic_values}
        end_time = time.time()
        print("consumed time:", end_time - start_time)

    return {
        'statusCode': 200,
        'body': json.dumps(output_dict)
    }
