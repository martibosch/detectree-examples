import contextily as ctx
import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors
from rasterio import plot, transform, warp
from shapely import geometry

from detectree_examples import settings

WEB_MERCATOR_CRS = (
    "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0"
    " +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +wktext  +no_defs"
)


def _reproject_raster(
    src_crs, src_arr, src_bounds, src_transform, dst_crs=WEB_MERCATOR_CRS, dst_nodata=0
):
    dst_transform, dst_width, dst_height = warp.calculate_default_transform(
        src_crs, dst_crs, src_arr.shape[1], src_arr.shape[0], *src_bounds
    )

    # use a float dtype so that the array can have nan values, which will be
    # transparent in the plot
    dst_arr = np.full((dst_height, dst_width), dst_nodata, dtype=src_arr.dtype)
    _ = warp.reproject(
        src_arr,
        dst_arr,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        dst_nodata=dst_nodata,
    )
    # dst_arr[dst_arr == 0] = np.nan
    return dst_arr, dst_transform


def plot_canopy(
    canopy_arr, canopy_transform, canopy_crs=None, num_steps=10, **subplots_kws
):
    """Plot canopy."""
    if canopy_crs is None:
        canopy_crs = settings.CRS

    # reproject the canopy array
    height, width = canopy_arr.shape[-2:]
    canopy_arr, canopy_transform = _reproject_raster(
        canopy_crs,
        canopy_arr,
        transform.array_bounds(height, width, canopy_transform),
        canopy_transform,
        dst_nodata=0,
    )

    # prepare the plot
    fig, ax = plt.subplots(**subplots_kws)

    # use geopandas plotting (with alpha 0) just to set the extent
    gpd.GeoSeries(
        [geometry.box(*transform.array_bounds(*canopy_arr.shape, canopy_transform))]
    ).plot(alpha=0, ax=ax)
    ctx.add_basemap(ax)

    # prepare a colormap for the trees
    tree_cmap = np.stack([[0, 0.5, 0, 0] for _ in range(num_steps)])
    # set alpha
    tree_cmap[:, -1] = np.linspace(0, 1, num_steps)
    # create new colormap
    tree_cmap = colors.ListedColormap(tree_cmap)

    # plot
    # if len(canopy_arr.shape) == 3:
    #     canopy_arr = canopy_arr
    plot.show(canopy_arr, transform=canopy_transform, ax=ax, cmap=tree_cmap)
    ax.set_axis_off()

    return ax
