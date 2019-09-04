import itertools
import logging
import os
from os import path
from urllib import request

import affine
import click
import pandas as pd
import rasterio as rio
from rasterio import windows
from rasterio.enums import Resampling
from tqdm import tqdm

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


def _get_tile_start(tile_filenames, tiles_dir):
    for k, tile_filename in enumerate(tile_filenames):
        tile_basename, tile_ext = path.splitext(tile_filename)
        for i in range(NUM_TILE_SUBDIVISIONS**2):
            if not path.exists(
                    _get_output_tile_filepath(tiles_dir, tile_basename, i,
                                              tile_ext)):
                return k


@click.command()
@click.argument('intersecting_tiles_csv_filepath',
                type=click.Path(exists=True))
@click.argument('tiles_dir', type=click.Path(exists=True))
@click.argument('output_filepath', type=click.Path())
@click.option('--resample-factor', type=int, required=False)
@click.option('--keep-raw', is_flag=True)
@click.option('--raw-dir', type=click.Path(exists=True), required=False)
def main(intersecting_tiles_csv_filepath, tiles_dir, output_filepath,
         resample_factor, keep_raw, raw_dir):
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

    # cache mechanism to avoid re-processing tiles that have already been
    # processed (e.g., after a download interruption)
    tile_start = _get_tile_start(tile_filenames, tiles_dir)
    if tile_start > 0:
        logger.info(
            "Skipping %d tiles because they have already been processed",
            tile_start)

    tiles_to_process = tile_filenames[tile_start:]
    output_tiles = []
    logger.info("Downloading and downscaling %d tiles from %s",
                len(tiles_to_process), BASE_URI)
    for tile_filename in tqdm(tiles_to_process):
        raw_tile_filepath = path.join(raw_dir, tile_filename)
        tile_basename, tile_ext = path.splitext(tile_filename)
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
                               transform=dst_transform)
                row_off, col_off = dst_window.row_off, dst_window.col_off
                tile_filepath = _get_output_tile_filepath(
                    tiles_dir, tile_basename, i, tile_ext)
                with rio.open(tile_filepath, 'w', **profile) as dst:
                    for channel in range(src.count):
                        dst.write(
                            data[channel][row_off:row_off +
                                          dst_window.height, col_off:col_off +
                                          dst_window.width], channel + 1)

                output_tiles.append(tile_filepath)

        # if raw tiles are not to be preserved, remove them at the end of each
        # iteration (with original 10cm resolution, they can take a lot of
        # local storage)
        if not keep_raw:
            os.remove(raw_tile_filepath)

    # if raw tiles are not to be preserved, remove the folder at the end
    # if not keep_raw:
    #     shutil.rmtree(raw_dir)

    # logger.info("Successfully dumped downscaled tiles to %s", tiles_dir)
    pd.Series(output_tiles).to_csv(output_filepath, header=False)
    logger.info("Dumped list of downscaled tiles to %s", output_filepath)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
