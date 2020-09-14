import itertools
import logging
import os
from os import path
from urllib import request

import affine
import click
import geopandas as gpd
import osmnx as ox
import pandas as pd
import rasterio as rio
import tqdm
from rasterio import windows
from rasterio.enums import Resampling
from shapely import geometry

from detectree_example import settings

BASE_URI = "https://maps.zh.ch/download/orthofoto/sommer/2014/rgb/jpeg/"
RESAMPLE_FACTOR = 5
NUM_TILE_SUBDIVISIONS = 5


def _get_window_transform(width, height, transform, num_tile_subdivisions):
    dst_width = width // num_tile_subdivisions
    dst_height = height // num_tile_subdivisions
    offsets = itertools.product(range(0, width, dst_width),
                                range(0, height, dst_height))
    big_window = windows.Window(col_off=0,
                                row_off=0,
                                width=width,
                                height=height)
    for col_off, row_off in offsets:
        dst_window = windows.Window(col_off=col_off,
                                    row_off=row_off,
                                    width=dst_width,
                                    height=dst_height).intersection(big_window)
        dst_transform = windows.transform(dst_window, transform)
        yield dst_window, dst_transform


def _get_output_tile_filepath(tiles_dir, tile_basename, tile_i, tile_ext):
    return path.join(tiles_dir, f"{tile_basename}_{tile_i:02}{tile_ext}")


@click.command()
@click.argument('intersecting_tiles_csv_filepath',
                type=click.Path(exists=True))
@click.argument('tiles_dir', type=click.Path(exists=True))
@click.argument('output_filepath', type=click.Path())
@click.option('--resample-factor', type=int, required=False)
@click.option('--keep-raw', is_flag=True)
@click.option('--raw-dir', type=click.Path(exists=True), required=False)
@click.option('--nominatim-query', required=False)
@click.option('--exclude-nominatim-query', required=False)
@click.option('--crs', required=False)
def main(intersecting_tiles_csv_filepath, tiles_dir, output_filepath,
         resample_factor, keep_raw, raw_dir, nominatim_query,
         exclude_nominatim_query, crs):
    logger = logging.getLogger(__name__)

    if resample_factor is None:
        resample_factor = RESAMPLE_FACTOR

    if raw_dir is None:
        raw_dir = 'data/raw/tiles'
        if not path.exists(raw_dir):
            os.mkdir(raw_dir)

    tile_filenames = pd.read_csv(intersecting_tiles_csv_filepath,
                                 index_col=0,
                                 header=None).iloc[:, 0]
    output_tiles = []
    for tile_filename in tqdm.tqdm(tile_filenames):
        raw_tile_filepath = path.join(raw_dir, tile_filename)
        tile_basename, tile_ext = path.splitext(tile_filename)
        if not path.exists(raw_tile_filepath):
            request.urlretrieve(BASE_URI + tile_filename, raw_tile_filepath)
        with rio.open(raw_tile_filepath) as src:
            interim_width = src.width // resample_factor
            interim_height = src.height // resample_factor
            data = src.read(out_shape=(src.count, interim_height,
                                       interim_width),
                            resampling=Resampling.average)
            t = src.transform
            interim_transform = affine.Affine(t.a * resample_factor, t.b, t.c,
                                              t.d, t.e * resample_factor, t.f)
            for i, (dst_window, dst_transform) in enumerate(
                    _get_window_transform(interim_width, interim_height,
                                          interim_transform,
                                          NUM_TILE_SUBDIVISIONS)):
                profile = src.profile.copy()
                profile.update(width=dst_window.width,
                               height=dst_window.height,
                               transform=dst_transform,
                               crs=settings.CRS)
                row_off, col_off = dst_window.row_off, dst_window.col_off
                tile_filepath = _get_output_tile_filepath(
                    tiles_dir, tile_basename, i, tile_ext)
                with rio.open(tile_filepath, 'w', **profile) as dst:
                    for channel in range(src.count):
                        dst.write(
                            data[channel][row_off:row_off + dst_window.height,
                                          col_off:col_off + dst_window.width],
                            channel + 1)

                output_tiles.append(tile_filepath)

        # if raw tiles are not to be preserved, remove them at the end of each
        # iteration (with original 10cm resolution, they can take a lot of
        # local storage)
        if not keep_raw:
            os.remove(raw_tile_filepath)

    # if raw tiles are not to be preserved, remove the folder at the end
    # if not keep_raw:
    #     shutil.rmtree(raw_dir)

    if nominatim_query:
        # get only the tiles that intersect the extent of the result of the
        # nominatim query
        logger.info("Querying Nominatim for boundaries for `%s`",
                    nominatim_query)
        gser = ox.geocode_to_gdf(nominatim_query)['geometry']
        if crs:
            pass
        else:
            crs = settings.CRS
        geom = gser.to_crs(crs).iloc[0]
        if exclude_nominatim_query:
            logger.info("Querying Nominatim for boundaries for `%s`",
                        exclude_nominatim_query)
            exclude_geom = ox.geocode_to_gdf(
                exclude_nominatim_query)['geometry'].to_crs(crs).iloc[0]
            geom = geom.difference(exclude_geom)

        def bbox_geom_from_tile(tile_filepath):
            with rio.open(tile_filepath) as src:
                return geometry.box(*src.bounds)

        tiles_gdf = gpd.GeoDataFrame(output_tiles,
                                     columns=['img_filepath'],
                                     geometry=list(
                                         map(bbox_geom_from_tile,
                                             output_tiles)),
                                     crs=crs)
        output_tiles_ser = gpd.sjoin(tiles_gdf,
                                     gpd.GeoDataFrame(geometry=[geom],
                                                      crs=crs),
                                     op='intersects',
                                     how='inner')['img_filepath']

        tiles_to_rm_ser = tiles_gdf['img_filepath'].loc[
            ~tiles_gdf.index.isin(output_tiles_ser.index)]
        for img_filepath in tiles_to_rm_ser:
            os.remove(img_filepath)
        logger.info(
            "removed %d tiles that do not intersect with the extent of %s",
            len(tiles_to_rm_ser), nominatim_query)
    else:
        # just create a pandas series anyway to use the `to_csv` method below
        output_tiles_ser = pd.Series(output_tiles)

    # logger.info("Successfully dumped downscaled tiles to %s", tiles_dir)
    output_tiles_ser.to_csv(output_filepath, header=False)
    logger.info("Dumped list of downscaled tiles to %s", output_filepath)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
