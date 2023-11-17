from osgeo import ogr, osr, gdal


def get_suffix_by_driver(driver_name: str):
    drive = gdal.GetDriverByName(driver_name)
    return drive.GetMetadataItem(gdal.DMD_EXTENSIONS).split(' ')[0]


def get_block_geom(min_x, max_x, min_y, max_y):
    point1 = min_x, max_y
    point2 = max_x, max_y
    point3 = max_x, min_y
    point4 = min_x, min_y
    # create ring
    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(*point1)
    ring.AddPoint(*point2)
    ring.AddPoint(*point3)
    ring.AddPoint(*point4)
    ring.AddPoint(*point1)
    # create polygon
    block = ogr.Geometry(ogr.wkbPolygon)
    block.AddGeometry(ring)

    return block


def add_feature_to_layer(layer: ogr.Layer, geom: ogr.Geometry, attribute_dict: dict):
    feature = ogr.Feature(layer.GetLayerDefn())
    for name, value in attribute_dict.items():
        feature.SetField(name, value)
    feature.SetGeometry(geom)
    layer.CreateFeature(feature)


def get_srs_from_epsg(epsg: int) -> osr.SpatialReference:
    srs = osr.SpatialReference()
    # very important, set axis order is lng-lat
    # details in https://gdal.org/tutorials/osr_api_tut.html
    srs.SetAxisMappingStrategy(0)
    srs.ImportFromEPSG(epsg)
    return srs
