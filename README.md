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

Example use case:

- [Aussersihl canopy](https://github.com/martibosch/detectree-examples/blob/main/notebooks/aussersihl-canopy.ipynb): application of DetecTree to compute a tree canopy map for the Aussersihl district in Zurich.

Overview of the train/test split methods:

- [Baseline](https://github.com/martibosch/detectree-examples/blob/main/notebooks/baseline.ipynb): train/test split of image tiles based on uniform sampling.
- [Cluster-I](https://github.com/martibosch/detectree-examples/blob/main/notebooks/cluster-I.ipynb): train/test split of image tiles based on *k*-means clustering of image descriptors to enhance the variety of scenes represented in the training tiles.
- [Cluster-II](https://github.com/martibosch/detectree-examples/blob/main/notebooks/cluster-II.ipynb): train/test split of image tiles based on a two-level *k*-means clustering, using a **separate classifier** for each first-level cluster of tiles. The second-level clustering enhances the variety of scenes represented in the training tiles of each separate classifier.

### Background

- [Background](https://github.com/martibosch/detectree-examples/blob/main/notebooks/background.ipynb): overview of the methods used to detect tree/non-tree pixels, based on Yang et al. [1]

## Instructions to reproduce

The materials of this repository make use of a set of external libraries, which are listed in the [environment.yml](https://github.com/martibosch/detectree-examples/blob/main/environment.yml) file. The easiest way to install such dependencies is by means of a [conda](https://docs.conda.io/en/latest/) environment:

1. Clone the repository and change directory to the repository's root:

```bash
git clone https://github.com/martibosch/detectree-examples
cd detectree-examples
```

2. Create the environment (this requires conda/mamba) and activate it:

```bash
# you can also use mamba
conda env create -f environment.yml
# the above command creates a conda environment named `detectree`
conda activate detectree
```

3. Register the IPython kernel of the `detectree` environment

```bash
python -m ipykernel install --user --name detectree --display-name "Python (detectree)"
```

You might now run a jupyter server (e.g., running the command `jupyter notebook`) and execute the notebooks of this repository.

## Makefile workflow

Some of the tasks of DetecTree's computational flow (e.g., computing image descriptors, training the classifiers...) can be computationally expensive. While Jupyter notebooks are a great medium to overview DetecTree's features, they are less convenient when it comes to managing complex computational workflows. In view of such shortcoming, this repository also includes a [Makefile](https://github.com/martibosch/detectree-examples/blob/main/Makefile) implementation of the computational workflow, which ensures the correct execution of the workflow and caches expensive intermediate results so that the workflow can be efficiently resumed at any point.

## Acknowledgments

- With the support of the École Polytechnique Fédérale de Lausanne (EPFL)
- The [aerial imagery](https://www.geolion.zh.ch/geodatensatz/2831) and [LIDAR](https://www.geolion.zh.ch/geodatensatz/show?gdsid=343) datasets used in this repository are provided by the [Office for spatial development (Amt für Raumentwicklung)](https://are.zh.ch/) of the canton of Zurich.
- Project based on the [cookiecutter data science project template](https://drivendata.github.io/cookiecutter-data-science). #cookiecutterdatascience

## References

1. Yang, L., Wu, X., Praun, E., & Ma, X. (2009). Tree detection from aerial imagery. In Proceedings of the 17th ACM SIGSPATIAL International Conference on Advances in Geographic Information Systems (pp. 131-137). ACM.
