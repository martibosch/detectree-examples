"""Make response tiles."""

import logging
from pathlib import Path

import click
import numpy as np
import pandas as pd
import pooch
import rasterio as rio
import swisstopopy
from detectree import settings as dtr_settings
from rasterio.windows import from_bounds
from tqdm.auto import tqdm

from detectree_examples import utils


def _match_response_to_img_extent(response_tile_filepath, img_filepath, nontree_val):
    """Write response tile on image grid, filling uncovered area as non-tree."""
    with (
        rio.open(img_filepath) as img_src,
        rio.open(response_tile_filepath) as response_src,
    ):
        dst_arr = np.full(
            (img_src.height, img_src.width),
            nontree_val,
            dtype=response_src.dtypes[0],
        )

        left = max(img_src.bounds.left, response_src.bounds.left)
        bottom = max(img_src.bounds.bottom, response_src.bounds.bottom)
        right = min(img_src.bounds.right, response_src.bounds.right)
        top = min(img_src.bounds.top, response_src.bounds.top)

        if left < right and bottom < top:
            src_window = (
                from_bounds(left, bottom, right, top, transform=response_src.transform)
                .round_offsets()
                .round_lengths()
            )
            dst_window = (
                from_bounds(left, bottom, right, top, transform=img_src.transform)
                .round_offsets()
                .round_lengths()
            )
            src_arr = response_src.read(1, window=src_window)

            row_off = int(dst_window.row_off)
            col_off = int(dst_window.col_off)
            row_end = min(row_off + src_arr.shape[0], img_src.height)
            col_end = min(col_off + src_arr.shape[1], img_src.width)

            if row_end > row_off and col_end > col_off:
                dst_arr[row_off:row_end, col_off:col_end] = src_arr[
                    : row_end - row_off, : col_end - col_off
                ]

        dst_profile = response_src.profile.copy()
        dst_profile.update(
            width=img_src.width,
            height=img_src.height,
            transform=img_src.transform,
            count=1,
            # dtype=dst_arr.dtype,
            nodata=nontree_val,
            crs=img_src.crs,
        )

    with rio.open(response_tile_filepath, "w", **dst_profile) as dst:
        dst.write(dst_arr, 1)


def make_response_tile(
    img_filepath, response_tile_filepath, surface3d_gdf, nontree_val
):
    """Make a response tile aligned to the input image tile extent."""
    # if surface3d_gdf is not None and not surface3d_gdf.empty:
    #     swisstopopy.get_tree_canopy_raster(
    #         surface3d_gdf=surface3d_gdf,
    #         dst_filepath=response_tile_filepath,
    #     )
    # else:
    #     # no LiDAR data for this tile (e.g., a lake: return an all non-tree mask on
    #     # the exact image grid
    #     pass
    swisstopopy.get_tree_canopy_raster(
        surface3d_gdf=surface3d_gdf,
        dst_filepath=response_tile_filepath,
    )
    _match_response_to_img_extent(response_tile_filepath, img_filepath, nontree_val)


def make_response_tiles(
    tile_filenames,
    region,
    img_dir,
    response_dir,
    *,
    year=None,
    overwrite=False,
    log_method=None,
):
    # print if no other logging method specified
    if log_method is None:
        log_method = print

    # we will match the SWISSIMAGE and swissSURFACE3D tiles by their ID because both
    # products share the same tiling, see (links in French):
    # - swisstopo.admin.ch/dam/fr/sd-web/WchyQCcLkyd9/Produktinfo_SWISSIMAGE10cm_FR.pdf
    # - swisstopo.admin.ch/dam/fr/sd-web/uIK9XXLTAGiI/swissSURFACE3D-ProdInfo-FR.pdf
    # alternatively, we could use spatial operations from geopandas, e.g., spatial joins
    # get training tile ids
    train_tile_ids = pd.Series(tile_filenames).apply(
        lambda img_filename: Path(img_filename).stem
    )

    # get swissSURFACE3D tiles
    log_method(f"Querying SwissTopo for swissSURFACE3D data in `{region}`")
    client = swisstopopy.SwissTopoClient(region)
    surface3d_gdf = client.get_collection_gdf(swisstopopy.SWISSSURFACE3D_COLLECTION_ID)
    # filter to get zip assets (LiDAR) only
    surface3d_gdf = surface3d_gdf[surface3d_gdf["assets.href"].str.endswith(".zip")]
    # add tile id column
    surface3d_gdf["tile_id"] = utils.surface3d_asset_id_to_tile_id(
        surface3d_gdf["assets.href"]
    )
    # select training tiles only
    surface3d_gdf = surface3d_gdf[surface3d_gdf["tile_id"].isin(train_tile_ids)]
    if year is None:
        # get latest imagery for each tile
        surface3d_gdf = swisstopopy.get_latest(surface3d_gdf)
    else:
        # get data from the target year only
        surface3d_gdf = surface3d_gdf[
            surface3d_gdf["properties.datetime"].dt.year == year
        ]

    # log found assets
    log_method(f"Found {len(surface3d_gdf)} swissSURFACE3D assets for train tiles")

    # ensure paths
    img_dir = Path(img_dir)
    response_dir = Path(response_dir)
    # get nontree val
    nontree_val = dtr_settings.NONTREE_VAL
    # logger.info("Using non-tree fill value from detectree.settings: %d", NONTREE_VAL)
    # download/rasterize tiles
    response_tile_filepaths = []
    for idx, tile_id in tqdm(
        zip(surface3d_gdf.index, surface3d_gdf["tile_id"]),
        total=len(surface3d_gdf),
    ):
        # ACHTUNG: we are hardcoding the file name but ideally we should get it from
        # surface3d_gdf
        img_filename = f"{tile_id}.tif"
        response_tile_filepath = response_dir / img_filename
        # avoid re-computing the tree canopy raster if we have done it already
        if response_tile_filepath.exists() and not overwrite:
            response_tile_filepaths.append(str(response_tile_filepath))
            continue

        # make response tile
        make_response_tile(
            img_dir / img_filename,
            response_tile_filepath,
            surface3d_gdf.loc[[idx]],
            nontree_val,
        )
        # log_method(f"Dumped response tile to {response_tile_filepath}")
        response_tile_filepaths.append(str(response_tile_filepath))

    return response_tile_filepaths


@click.command()
@click.argument("split_csv_filepath", type=click.Path(exists=True))
@click.argument("region")
@click.argument("img_dir", type=click.Path(exists=True))
@click.argument("response_dir", type=click.Path(exists=True))
@click.argument("dst_filepath", type=click.Path())
@click.option(
    "--year",
    type=int,
    default=None,
    show_default=True,
    help="SWISSIMAGE acquisition year, default to the latest available.",
)
@click.option("--overwrite", is_flag=True, help="Recompute existing response tiles.")
def main(
    split_csv_filepath, region, response_dir, img_dir, dst_filepath, year, overwrite
):
    """Build response tiles from swissSURFACE3D for training tiles."""
    logger = logging.getLogger(__name__)

    # disable pooch logs
    pooch.get_logger().setLevel(logging.ERROR)

    # get training tiles from split
    split_df = pd.read_csv(split_csv_filepath)

    response_tile_filepaths = make_response_tiles(
        split_df[split_df["train"]]["img_filename"],
        region,
        img_dir,
        response_dir,
        year=year,
        overwrite=overwrite,
        log_method=logger.info,
    )

    pd.Series(response_tile_filepaths).to_csv(dst_filepath, index=False, header=False)
    logger.info("Dumped list of response tiles to %s", dst_filepath)


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
