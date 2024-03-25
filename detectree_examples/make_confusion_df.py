import random

import dask
import detectree as dtr
import numpy as np
import pandas as pd
from dask import diagnostics

from detectree_examples import make_response_tiles


def _inner_loop(img_filepath, lidar_gdf, lidar_raw_dir, c, clf):
    truth_arr = make_response_tiles.make_response_tile(
        img_filepath, lidar_gdf, lidar_raw_dir
    )
    pred_arr = c.classify_img(img_filepath, clf)
    return np.array((truth_arr.flatten(), pred_arr.flatten()))


def _get_validation_df(split_df, n, frac):
    return split_df[~split_df["train"]].sample(n=n, frac=frac)


def make_confusion_df(
    lidar_gdf,
    lidar_raw_dir,
    split_df=None,
    img_filepaths=None,
    n=None,
    frac=0.05,
    clf=None,
    clf_dict=None,
):

    c = dtr.Classifier()
    truth_pred_lazy = []
    if clf is not None:
        if split_df is None:
            num_validation_tiles = int(frac * len(img_filepaths))
            test_filepaths = random.choices(img_filepaths, k=num_validation_tiles)
        else:
            test_filepaths = _get_validation_df(split_df, n, frac)["img_filepath"]

        for img_filepath in test_filepaths:
            truth_pred_lazy.append(
                dask.delayed(_inner_loop)(
                    img_filepath, lidar_gdf, lidar_raw_dir, c, clf
                )
            )
    else:
        validation_df = _get_validation_df(split_df, n, frac)
        for img_cluster, cluster_df in validation_df.groupby("img_cluster"):
            clf = clf_dict[img_cluster]
            for img_filepath in cluster_df["img_filepath"]:
                truth_pred_lazy.append(
                    dask.delayed(_inner_loop)(
                        img_filepath, lidar_gdf, lidar_raw_dir, c, clf
                    )
                )

    with diagnostics.ProgressBar():
        truth_pred = np.hstack(dask.compute(*truth_pred_lazy))

    truth_ser = pd.Series(truth_pred[0], name="actual")
    pred_ser = pd.Series(truth_pred[1], name="predicted")
    return pd.crosstab(truth_ser, pred_ser) / len(truth_ser)
