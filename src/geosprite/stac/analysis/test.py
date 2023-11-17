import rasterio
from lambda_function import lambda_handler


def main():
    event = {
        "geojson": {
"type": "FeatureCollection",
"name": "aws_test",
"crs": { "type": "name", "properties": { "name": "urn:ogc:def:crs:OGC:1.3:CRS84" } },
"features": [
{ "type": "Feature", "properties": { }, "geometry": { "type": "MultiPolygon", "coordinates": [ [ [ [ 96.231337877960598, 33.111550337935988 ], [ 96.221632376539333, 33.030920018436206 ], [ 96.427687637483217, 32.986125396491879 ], [ 96.419475290126755, 33.123495570454473 ], [ 96.346310740951026, 33.191434080403369 ], [ 96.231337877960598, 33.111550337935988 ] ] ] ] } }
]
},
        "product_name": "water_distribution",
        "year": "2020",
        "statistic_values": [0, 1]
    }

    answer = lambda_handler(event=event, context="nothing to say")
    print(answer)


if __name__ == "__main__":
    main()
