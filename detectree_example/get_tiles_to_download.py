import logging

import click
import geopandas as gpd
import osmnx as ox


@click.command()
@click.argument('tiles_shp_filepath', type=click.Path(exists=True))
@click.argument('nominatim_query')
@click.argument('output_filepath', type=click.Path())
@click.option('--op', default='within')
def main(tiles_shp_filepath, nominatim_query, output_filepath, op):
    logger = logging.getLogger(__name__)

    tiles_gdf = gpd.read_file(tiles_shp_filepath)
    # get boundary
    logger.info("Querying Nominatim for boundaries for `%s`", nominatim_query)
    geom = ox.gdf_from_place(nominatim_query)['geometry'].to_crs(
        tiles_gdf.crs).iloc[0]

    # get the filename of the tiles whose geometry is within with the
    # municipal boundaries
    op_method = getattr(tiles_gdf['geometry'], op)
    tile_filename_ser = tiles_gdf[op_method(geom)]['location']
    logger.info("Found %d intersecting tiles", len(tile_filename_ser))
    tile_filename_ser.to_csv(output_filepath, header=False)
    logger.info("Dumped list of intersecting tiles to %s", output_filepath)


if __name__ == '__main__':
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)

    main()
