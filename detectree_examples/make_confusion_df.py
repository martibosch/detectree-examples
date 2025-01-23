import random
from os import path

import dask
import detectree as dtr
import numpy as np
import pandas as pd
import rasterio as rio
from dask import diagnostics

from detectree_examples import make_response_tiles


def _inner_loop(img_filepath, lidar_gdf, lidar_raw_dir, response_dir, c, clf):
    pred_arr = c._predict_img(img_filepath, clf)
    response_tile_filepath = make_response_tiles.make_response_tile(
        img_filepath, lidar_gdf, lidar_raw_dir, response_dir
    )
    with rio.open(response_tile_filepath) as src:
        return np.array((src.read(1).flatten(), pred_arr.flatten()))


def _get_validation_df(split_df, n, frac):
    return split_df[~split_df["train"]].sample(n=n, frac=frac)


def make_confusion_df(
    lidar_gdf,
    lidar_raw_dir,
    response_dir,
    *,
    split_df=None,
    img_filepaths=None,
    img_dir=None,
    n=None,
    frac=0.05,
    clf=None,
    clf_dict=None,
):
    """Make confusion data frame."""
    # this is not how the detectree v0.5.0 is supposed to work but there is no need to
    # change it here.
    # TODO: add detectree method to compute confusion matrix (e.g., return list of image
    # arrays in `predict_imgs`)
    c = dtr.Classifier(clf=clf, clf_dict=clf_dict)
    truth_pred_lazy = []
    if clf is not None:
        if split_df is None:
            num_validation_tiles = int(frac * len(img_filepaths))
            test_filepaths = random.choices(img_filepaths, k=num_validation_tiles)
        else:
            test_filepaths = _get_validation_df(split_df, n, frac)[
                "img_filename"
            ].apply(lambda img_filename: path.join(img_dir, img_filename))
        for img_filepath in test_filepaths:
            truth_pred_lazy.append(
                dask.delayed(_inner_loop)(
                    img_filepath,
                    lidar_gdf,
                    lidar_raw_dir,
                    response_dir,
                    c,
                    clf,
                )
            )
    else:
        validation_df = _get_validation_df(split_df, n, frac)
        for img_cluster, cluster_df in validation_df.groupby("img_cluster"):
            clf = clf_dict[img_cluster]
            for img_filepath in cluster_df["img_filename"].apply(
                lambda img_filename: path.join(img_dir, img_filename)
            ):
                truth_pred_lazy.append(
                    dask.delayed(_inner_loop)(
                        img_filepath, lidar_gdf, lidar_raw_dir, response_dir, c, clf
                    )
                )

    with diagnostics.ProgressBar():
        truth_pred = np.hstack(dask.compute(*truth_pred_lazy))

    truth_ser = pd.Series(truth_pred[0], name="actual")
    pred_ser = pd.Series(truth_pred[1], name="predicted")
    return pd.crosstab(truth_ser, pred_ser) / len(truth_ser)


def compute_metrics(confusion_df):
    """Compute accuracy, precision, recall and f1 from a confusion matrix."""
    accuracy = np.trace(confusion_df)
    tp = confusion_df.loc[255, 255]
    fp = confusion_df.loc[0, 255]
    fn = confusion_df.loc[255, 0]
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    f1 = 2 * (precision * recall) / (precision + recall)
    return accuracy, precision, recall, f1
