"""Make tiles."""

import logging

import click
import pandas as pd
import pooch
import swisstopopy
from tqdm.auto import tqdm

from detectree_examples import utils


@click.command()
@click.argument("region")
@click.argument("img_dir", type=click.Path(exists=True))
@click.argument("dst_filepath", type=click.Path())
@click.option(
    "--year",
    type=int,
    default=None,
    show_default=True,
    help="SWISSIMAGE acquisition year, default to the latest available.",
)
@click.option(
    "--img-res",
    type=float,
    default=2,
    show_default=True,
    help="SWISSIMAGE resolution in meters (0.1 or 2).",
)
def main(
    region,
    img_dir,
    dst_filepath,
    year,
    img_res,
):
    """Get and download the latest SWISSIMAGE tiles for a region."""
    logger = logging.getLogger(__name__)

    pooch.get_logger().setLevel(logging.ERROR)

    logger.info("Querying SwissTopo for SWISSIMAGE tiles in `%s`", region)
    client = swisstopopy.SwissTopoClient(region)
    swissimage_gdf = client.get_collection_gdf(swisstopopy.SWISSIMAGE10_COLLECTION_ID)
    # get the target resolution only
    swissimage_gdf = swissimage_gdf[swissimage_gdf["assets.eo:gsd"] == img_res]
    if year is None:
        # get latest imagery for each tile
        swissimage_gdf = swisstopopy.get_latest(swissimage_gdf)
    else:
        # get data from the target year only
        swissimage_gdf = swissimage_gdf[
            swissimage_gdf["properties.datetime"].dt.year == year
        ]
    logger.info(
        "Found %d intersecting SWISSIMAGE tiles to download", len(swissimage_gdf)
    )

    # download files using pooch
    # we provide a custom `fname` so that we can match SWISSIMAGE and swissSURFACE3D
    # tiles by filename more easily
    img_filepaths = [
        pooch.retrieve(img_url, known_hash=None, fname=f"{tile_id}.tif", path=img_dir)
        for img_url, tile_id in tqdm(
            zip(
                swissimage_gdf["assets.href"],
                utils.swissimage_asset_id_to_tile_id(swissimage_gdf["id"]),
            ),
            total=len(swissimage_gdf),
        )
    ]
    logger.info("Downloaded %d tiles to %s", len(swissimage_gdf), img_dir)

    # dump list of output tiles
    pd.Series(img_filepaths).to_csv(dst_filepath, index=False, header=False)
    logger.info("Dumped list of downloaded tiles to %s", dst_filepath)


if __name__ == "__main__":
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
