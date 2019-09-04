import logging

import click
import geopandas as gpd
from slugify import slugify

AGGLOMERATION_SLUG = "zurich"


@click.command()
@click.argument('tiles_shp_filepath', type=click.Path(exists=True))
@click.argument('gmb_filepath', type=click.Path(exists=True))
@click.argument('output_filepath', type=click.Path())
def main(tiles_shp_filepath, gmb_filepath, output_filepath):
    logger = logging.getLogger(__name__)

    logger.info("Intersecting tiles with %s agglomeration extent",
                AGGLOMERATION_SLUG)
    tiles_gdf = gpd.read_file(tiles_shp_filepath)
    # get Zurich's municipal boundary
    gdf = gpd.read_file(gmb_filepath)
    municipal_geom = gdf[gdf['GMDNAME'].apply(slugify).str.contains(
        AGGLOMERATION_SLUG)]['geometry'].unary_union
    # get the filename of the tiles whose geometry is within with the
    # municipal boundaries
    tile_filename_ser = tiles_gdf[tiles_gdf['geometry'].within(
        municipal_geom)]['location']
    logger.info("Found %d intersecting tiles", len(tile_filename_ser))
    tile_filename_ser.to_csv(output_filepath, header=False)
    logger.info("Dumped list of intersecting tiles to %s", output_filepath)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
