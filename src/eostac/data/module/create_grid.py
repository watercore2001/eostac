import math

from osgeo import ogr

from eostac.data.module.utils import get_block_geom, get_srs_from_epsg, add_feature_to_layer

SHP_DRIVER = ogr.GetDriverByName("ESRI Shapefile")
WGS84_EPSG = 4326


def create_grid(input_shp_path: str, degrees: tuple[int, int], output_shp_path: str):
    input_ds = SHP_DRIVER.Open(input_shp_path, 0)
    input_layer = input_ds.GetLayer()
    input_feature = input_layer.GetFeature(0)
    input_geometry = input_feature.GetGeometryRef()

    output_ds = SHP_DRIVER.CreateDataSource(output_shp_path)
    wgs84_srs = get_srs_from_epsg(WGS84_EPSG)
    output_layer = output_ds.CreateLayer("grid", wgs84_srs, ogr.wkbPolygon)
    # add field
    output_layer.CreateField(ogr.FieldDefn("id", ogr.OFTString))
    output_layer.CreateField(ogr.FieldDefn("lng_min", ogr.OFTInteger))
    output_layer.CreateField(ogr.FieldDefn("lng_max", ogr.OFTInteger))
    output_layer.CreateField(ogr.FieldDefn("lat_min", ogr.OFTInteger))
    output_layer.CreateField(ogr.FieldDefn("lat_max", ogr.OFTInteger))
    for lng_min in range(-180, 180, degrees[0]):
        for lat_min in range(-90, 90, degrees[1]):
            block_geom = get_block_geom(lng_min, lng_min + degrees[0], lat_min, lat_min + degrees[1])
            if not block_geom.Intersect(input_geometry):
                continue
            intersection_geom = block_geom.Intersection(input_geometry)
            block_lng_min, block_lng_max, block_lat_min, block_lat_max = intersection_geom.GetEnvelope()
            intersect_block_geom = get_block_geom(block_lng_min, block_lng_max, block_lat_min, block_lat_max)

            attribute = {"id": f"E{lng_min}N{lat_min}",
                         "lng_min": math.floor(block_lng_min), "lng_max": math.ceil(block_lng_max),
                         "lat_min": math.floor(block_lat_min), "lat_max": math.ceil(block_lat_max)}
            add_feature_to_layer(output_layer, intersect_block_geom, attribute)


if __name__ == "__main__":
    create_grid(r"C:\Users\watercore\Desktop\data\hkh\outline\outline.shp", (5, 5),
                r"C:\Users\watercore\Desktop\data\hkh\outline\grid2.shp")
