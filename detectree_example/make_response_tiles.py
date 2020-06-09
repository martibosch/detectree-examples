import logging
import os
from os import path
from urllib import request

import click
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio as rio
from laspy import file as lp_file
from rasterio import enums, features
from scipy import ndimage as ndi
from shapely import geometry

BASE_URI = "https://maps.zh.ch/download/hoehen/2014/lidar/"


def get_from_cache_or_download(lidar_tile_filename,
                               cache_dir,
                               bounds,
                               logger=None):
    local_tile_filepath = path.join(cache_dir, lidar_tile_filename)
    if not path.exists(local_tile_filepath):
        lidar_uri = BASE_URI + lidar_tile_filename
        if logger is not None:
            logger.info("Downloading LIDAR data from %s to %s", lidar_uri,
                        local_tile_filepath)
        request.urlretrieve(lidar_uri, local_tile_filepath)

    with lp_file.File(local_tile_filepath, mode='r') as src:
        c = src.get_classification()
        x = src.x
        y = src.y

    cond = ((c == 4) ^ (c == 5)) & ((x >= bounds.left) & (x <= bounds.right) &
                                    (y >= bounds.bottom) & (y <= bounds.top))
    return pd.DataFrame({'class_val': c[cond], 'x': x[cond], 'y': y[cond]})


def make_response_tile(tile_filepath,
                       lidar_gdf,
                       raw_dir,
                       response_dir=None,
                       output_dtype=rio.uint8,
                       output_tree_val=255,
                       output_nodata=0,
                       high_veg_val=5,
                       logger=None):
    with rio.open(tile_filepath) as src:
        bounds = src.bounds
        lidar_tile_filenames = lidar_gdf[lidar_gdf['geometry'].intersects(
            geometry.box(*bounds))]['dateiname']

        dfs = []
        for lidar_tile_filename in lidar_tile_filenames:
            dfs.append(
                get_from_cache_or_download(lidar_tile_filename, raw_dir,
                                           bounds))
        df = pd.concat(dfs)
        gser = gpd.GeoSeries(
            [geometry.Point(x, y) for x, y in zip(df['x'], df['y'])])
        arr = features.rasterize(shapes=[
            (geom, class_val)
            for geom, class_val in zip(gser, df['class_val'])
        ],
                                 out_shape=src.shape,
                                 transform=src.transform,
                                 merge_alg=enums.MergeAlg('ADD'))

        output_arr = ndi.binary_opening(
            arr >= high_veg_val).astype(output_dtype) * output_tree_val
        if response_dir is not None:
            meta = src.meta.copy()

    if response_dir is not None:
        meta.update(dtype=output_dtype, count=1, nodata=output_nodata)
        response_tile_filepath = path.join(response_dir,
                                           path.basename(tile_filepath))
        with rio.open(response_tile_filepath, 'w', **meta) as dst:
            dst.write(output_arr, 1)
        if logger is not None:
            logger.info("Dumped response tile to %s", response_tile_filepath)
        return response_tile_filepath
    else:
        return output_arr


def make_response_tiles(split_df,
                        lidar_gdf,
                        raw_dir,
                        response_dir=None,
                        logger=None):
    tile_filepaths = split_df[split_df['train']]['img_filepath']

    response_tile_filepaths = []
    for tile_filepath in tile_filepaths:
        response_tile_filepath = make_response_tile(tile_filepath,
                                                    lidar_gdf,
                                                    raw_dir,
                                                    response_dir=response_dir,
                                                    logger=logger)
        response_tile_filepaths.append(response_tile_filepath)

    return response_tile_filepaths


@click.command()
@click.argument('split_csv_filepath', type=click.Path(exists=True))
@click.argument('lidar_shp_filepath', type=click.Path(exists=True))
@click.argument('response_dir', type=click.Path(exists=True))
@click.argument('output_filepath', type=click.Path())
@click.option('--high-veg-val', type=int, default=5)
@click.option('--output-tree-val', type=int, default=255)
@click.option('--output-nodata', type=int, default=0)
@click.option('--raw-dir', type=click.Path(exists=True), required=False)
def main(split_csv_filepath, lidar_shp_filepath, response_dir, output_filepath,
         high_veg_val, output_tree_val, output_nodata, raw_dir):
    logger = logging.getLogger(__name__)

    if raw_dir is None:
        raw_dir = 'data/raw/lidar'
        if not path.exists(raw_dir):
            os.mkdir(raw_dir)

    split_df = pd.read_csv(split_csv_filepath)
    tile_filepaths = split_df[split_df['train']]['img_filepath']

    lidar_gdf = gpd.read_file(lidar_shp_filepath)
    response_tile_filepaths = []
    for tile_filepath in tile_filepaths:
        response_tile_filepath = make_response_tile(
            tile_filepath,
            lidar_gdf,
            raw_dir,
            response_dir=response_dir,
            output_tree_val=output_tree_val,
            output_nodata=output_nodata,
            high_veg_val=high_veg_val,
            logger=logger)
        response_tile_filepaths.append(response_tile_filepath)

    # if not keep_raw:
    #     shutil.rmtree(raw_dir)

    pd.Series(response_tile_filepaths).to_csv(output_filepath, header=False)
    logger.info("Dumped list of response tiles to %s", output_filepath)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
