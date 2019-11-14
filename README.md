[![GitHub license](https://img.shields.io/github/license/martibosch/detectree-example.svg)](https://github.com/martibosch/detectree-example/blob/master/LICENSE)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/martibosch/detectree-example/master?filepath=notebooks)

# DetecTree example

Example computational workflows to classify tree/non-tree pixels in Zurich using [DetecTree](https://github.com/martibosch/detectree).

See the list of notebooks below (the notebooks are stored in the [`notebooks` folder](https://github.com/martibosch/detectree-example/blob/master/notebooks)):

### Background

* [Background](https://github.com/martibosch/detectree-example/blob/master/notebooks/background.ipynb): overview of the methods used to detect tree/non-tree pixels, based on Yang et al. [1]

### Example workflows

* [Baseline](https://github.com/martibosch/detectree-example/blob/master/notebooks/baseline.ipynb): train/test split of image tiles based on uniform sampling.
* [Cluster-I](https://github.com/martibosch/detectree-example/blob/master/notebooks/cluster-I.ipynb): train/test split of image tiles based on *k*-means clustering of image descriptors to enhance the variety of scenes represented in the training tiles.
* [Cluster-II](https://github.com/martibosch/detectree-example/blob/master/notebooks/cluster-II.ipynb): train/test split of image tiles based on a two-level *k*-means clustering, using a **separate classifier** for each first-level cluster of tiles. The second-level clustering enhances the variety of scenes represented in the training tiles of each separate classifier.

### Makefile workflow

Some of the tasks of DetecTree's computational flow (e.g., computing image descriptors, training the classifiers...) can be computationally expensive. While Jupyter notebooks are a great medium to overview DetecTree's features, they are less convenient when it comes to managing complex computational workflows. In view of such shortcoming, this repository also includes a [Makefile](https://github.com/martibosch/detectree-example/blob/master/Makefile) implementation of the computational workflow, which ensures the correct execution of the workflow and caches expensive intermediate results so that the workflow can be efficiently resumed at any point.

## Acknowledgments

* With the support of the École Polytechnique Fédérale de Lausanne (EPFL)
* The [aerial imagery](https://www.geolion.zh.ch/geodatensatz/2831) and [LIDAR](https://www.geolion.zh.ch/geodatensatz/show?gdsid=343) datasets used in this repository are provided by the [Office for spatial development (Amt für Raumentwicklung)](https://are.zh.ch/) of the canton of Zurich.
* Project based on the [cookiecutter data science project template](https://drivendata.github.io/cookiecutter-data-science). #cookiecutterdatascience


## References

1. Yang, L., Wu, X., Praun, E., & Ma, X. (2009). Tree detection from aerial imagery. In Proceedings of the 17th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems (pp. 131-137). ACM.
