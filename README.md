[![GitHub license](https://img.shields.io/github/license/martibosch/detectree-examples.svg)](https://github.com/martibosch/detectree-examples/blob/main/LICENSE)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/martibosch/detectree-examples/main?filepath=notebooks)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/martibosch/detectree-examples/main.svg)](https://results.pre-commit.ci/latest/github/martibosch/detectree-examples/main)

# DetecTree example

Example computational workflows to classify tree/non-tree pixels in Zurich using [DetecTree](https://github.com/martibosch/detectree).

## Citation

Bosch M. 2020. “DetecTree: Tree detection from aerial imagery in Python”. *Journal of Open Source Software, 5(50), 2172.* [doi.org/10.21105/joss.02172](https://doi.org/10.21105/joss.02172)

## Notebooks

The notebooks are stored in the [`notebooks` folder](https://github.com/martibosch/detectree-examples/blob/main/notebooks). If you have trouble reproducing them, see the "Instructions to reproduce" section below.

### Pre-trained model

- [Pre-trained model](https://github.com/martibosch/detectree-examples/blob/main/notebooks/pre-trained-model.ipynb): examples of using the pre-trained model to detect trees in aerial imagery from different sources.

### Training

- [Aussersihl canopy](https://github.com/martibosch/detectree-examples/blob/main/notebooks/aussersihl-canopy.ipynb): application of DetecTree to compute a tree canopy map for the Aussersihl district in Zurich.
- [Cluster-I](https://github.com/martibosch/detectree-examples/blob/main/notebooks/cluster-I.ipynb): train/test split of image tiles based on *k*-means clustering of image descriptors to enhance the variety of scenes represented in the training tiles.

**Out-of-date notebooks** on other train/test split methods:

- [Baseline](https://github.com/martibosch/detectree-examples/blob/main/notebooks/baseline.ipynb): train/test split of image tiles based on uniform sampling.
- [Cluster-II](https://github.com/martibosch/detectree-examples/blob/main/notebooks/cluster-II.ipynb): train/test split of image tiles based on a two-level *k*-means clustering, using a **separate classifier** for each first-level cluster of tiles. The second-level clustering enhances the variety of scenes represented in the training tiles of each separate classifier.

### Background

- [Background](https://github.com/martibosch/detectree-examples/blob/main/notebooks/background.ipynb): overview of the methods used to detect tree/non-tree pixels, based on Yang et al. [1]

## Instructions to reproduce

This setup uses [pixi](https://github.com/prefix-dev/pixi) to manage dependencies. With pixi installed in your system, you can simply run `pixi run python` and you will get a Python shell session with all the dependencies available. In order to run notebooks within this environment, you can use [pixi-kernel](https://github.com/renan-r-santos/pixi-kernel).

## Acknowledgments

- The [aerial imagery](https://www.swisstopo.admin.ch/en/orthoimage-swissimage-10) and [LIDAR](https://www.swisstopo.admin.ch/en/height-model-swisssurface3d) datasets used in this repository are provided by the [Federal Office of Topography swisstopo](https://www.swisstopo.admin.ch/en).
- Based on the [cookiecutter-data-snake :snake:](https://github.com/martibosch/cookiecutter-data-snake) template for reproducible data science.

## References

1. Yang, L., Wu, X., Praun, E., & Ma, X. (2009). Tree detection from aerial imagery. In Proceedings of the 17th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems (pp. 131-137). ACM.
