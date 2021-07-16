.PHONY: tiles train_test_split download_lidar_shp response_tiles train_models \
	predict_tiles aussersihl_tiles execute_notebooks

#################################################################################

# globals

## variables
CODE_DIR = detectree_example

DATA_DIR = data
DATA_RAW_DIR := $(DATA_DIR)/raw
DATA_INTERIM_DIR := $(DATA_DIR)/interim
DATA_PROCESSED_DIR := $(DATA_DIR)/processed

## rules
define MAKE_DATA_SUB_DIR
$(DATA_SUB_DIR): | $(DATA_DIR)
	mkdir $$@
endef
$(DATA_DIR):
	mkdir $@
$(foreach DATA_SUB_DIR, \
	$(DATA_RAW_DIR) $(DATA_INTERIM_DIR) $(DATA_PROCESSED_DIR), \
		$(eval $(MAKE_DATA_SUB_DIR)))

# main workflow
## tiles

### variables
#### Zurich orthofoto https://www.geolion.zh.ch/geodatensatz/2831
ORTHOIMG_URI_BASE = \
	https://maps.zh.ch/download/orthofoto/sommer/2014/rgb/jpeg/ortho_sommer14
ORTHOIMG_SHP_EXTENSIONS = dbf prj shx
ORTHOIMG_SHP_DIR := $(DATA_RAW_DIR)/orthoimg
ORTHOIMG_SHP_BASEPATH := $(ORTHOIMG_SHP_DIR)/ortho_sommer14
ORTHOIMG_SHP_OTHERS := $(foreach EXT, $(ORTHOIMG_SHP_EXTENSIONS), \
	$(ORTHOIMG_SHP_BASEPATH).$(EXT))
ORTHOIMG_SHP := $(ORTHOIMG_SHP_BASEPATH).shp

#### Download the required tiles of the orthoimage
TILES_DIR = $(DATA_INTERIM_DIR)/tiles
INTERSECTING_TILES_CSV := $(TILES_DIR)/intersecting_tiles.csv
DOWNSAMPLED_TILES_CSV := $(TILES_DIR)/downsampled_tiles.csv
NOMINATIM_QUERY = Zurich  # municipal boundaries

#### code
GET_TILES_TO_DOWNLOAD_PY = $(CODE_DIR)/get_tiles_to_download.py
MAKE_TILES_PY = $(CODE_DIR)/make_tiles.py

### rules
$(ORTHOIMG_SHP_DIR): | $(DATA_RAW_DIR)
	mkdir $@
define DOWNLOAD_ORTHOIMG_SHP
$(ORTHOIMG_SHP_OTHER): | $(ORTHOIMG_SHP_DIR)
	wget $(ORTHOIMG_URI_BASE)$$(suffix $$@) -O $$@
endef
$(foreach ORTHOIMG_SHP_OTHER, $(ORTHOIMG_SHP_OTHERS), \
	$(eval $(DOWNLOAD_ORTHOIMG_SHP)))
$(ORTHOIMG_SHP): $(ORTHOIMG_SHP_OTHERS)
	wget $(ORTHOIMG_URI_BASE)$(suffix $@) -O $@

$(TILES_DIR): | $(DATA_INTERIM_DIR)
	mkdir $@
$(INTERSECTING_TILES_CSV): $(GET_TILES_TO_DOWNLOAD_PY) $(ORTHOIMG_SHP) \
	| $(TILES_DIR)
	python $(GET_TILES_TO_DOWNLOAD_PY) $(ORTHOIMG_SHP) $(NOMINATIM_QUERY) $@
$(DOWNSAMPLED_TILES_CSV): $(INTERSECTING_TILES_CSV) $(MAKE_TILES_PY) \
	| $(TILES_DIR)
	python $(MAKE_TILES_PY) $< $(TILES_DIR) $@ \
		--nominatim-query $(NOMINATIM_QUERY)
tiles: $(DOWNSAMPLED_TILES_CSV)

## train/test split

### variables
TRAIN_TEST_SPLIT_CSV := $(TILES_DIR)/split.csv
NUM_TILE_CLUSTERS = 4

### rules
$(TRAIN_TEST_SPLIT_CSV): $(MUNICIPAL_TILES_CSV)
	detectree train-test-split --img-dir $(MUNICIPAL_TILES_DIR) \
		--output-filepath $(TRAIN_TEST_SPLIT_CSV) \
		--num-img-clusters $(NUM_TILE_CLUSTERS)
train_test_split: $(TRAIN_TEST_SPLIT_CSV)


## response tiles

### variables
#### Zurich lidar https://www.geolion.zh.ch/geodatensatz/2606
LIDAR_URI_BASE = https://maps.zh.ch/download/hoehen/2014/lidar/lidar2014
LIDAR_SHP_EXTENSIONS = dbf prj qix shx
LIDAR_SHP_DIR = $(DATA_RAW_DIR)/lidar
LIDAR_SHP_BASEPATH := $(LIDAR_SHP_DIR)/lidar2014
LIDAR_SHP_OTHERS := $(foreach EXT, $(LIDAR_SHP_EXTENSIONS), \
	$(LIDAR_SHP_BASEPATH).$(EXT))
LIDAR_SHP := $(LIDAR_SHP_BASEPATH).shp

RESPONSE_TILES_DIR := $(DATA_INTERIM_DIR)/response_tiles
MAKE_RESPONSE_TILES_PY = $(CODE_DIR)/make_response_tiles.py
RESPONSE_TILES_CSV := $(RESPONSE_TILES_DIR)/response_tiles.csv

### rules
$(LIDAR_SHP_DIR): | $(DATA_RAW_DIR)
	mkdir $@
define DOWNLOAD_LIDAR_SHP
$(LIDAR_SHP_OTHER): | $(LIDAR_SHP_DIR)
	wget $(LIDAR_URI_BASE)$$(suffix $$@) -O $$@
	touch $$@
endef
$(foreach LIDAR_SHP_OTHER, $(LIDAR_SHP_OTHERS), \
	$(eval $(DOWNLOAD_LIDAR_SHP)))
$(LIDAR_SHP): $(LIDAR_SHP_OTHERS)
	wget $(LIDAR_URI_BASE)$(suffix $@) -O $@
	touch $@
download_lidar_shp: $(LIDAR_SHP)

$(RESPONSE_TILES_DIR): | $(DATA_INTERIM_DIR)
	mkdir $@
$(RESPONSE_TILES_CSV): $(TRAIN_TEST_SPLIT_CSV) $(LIDAR_SHP) \
	$(MAKE_RESPONSE_TILES_PY) | $(RESPONSE_TILES_DIR)
	python $(MAKE_RESPONSE_TILES_PY) $(TRAIN_TEST_SPLIT_CSV) $(LIDAR_SHP) \
		$(RESPONSE_TILES_DIR) $@
response_tiles: $(RESPONSE_TILES_CSV)


## train models

### variables
MODELS_DIR = models
MODEL_JOBLIB_FILEPATHS := $(foreach CLUSTER_LABEL, \
	$(shell seq 0 $$(($(NUM_TILE_CLUSTERS)-1))), \
		$(MODELS_DIR)/$(CLUSTER_LABEL).joblib)

### rules
$(MODELS_DIR):
	mkdir $@

$(MODELS_DIR)/%.joblib: $(RESPONSE_TILES_CSV) $(TRAIN_TEST_SPLIT_CSV) \
	| $(MODELS_DIR)
	detectree train-classifier --split-filepath $(TRAIN_TEST_SPLIT_CSV) \
		--response-img-dir $(RESPONSE_TILES_DIR) --img-cluster $* \
		--output-filepath $@
train_models: $(MODEL_JOBLIB_FILEPATHS)


## predict

### variables
predict_tiles: $(MODEL_JOBLIB_FILEPATHS) $(TRAIN_TEST_SPLIT_CSV) \
	| $(DATA_PROCESSED_DIR)
	detectree classify-imgs --clf-dir $(MODELS_DIR) \
		--output-dir $(DATA_PROCESSED_DIR) $(TRAIN_TEST_SPLIT_CSV)

# Aussersihl
## make a LULC raster for Zurich's Aussersihl
### variables
AUSSERSIHL_NOMINATIM_QUERY = "Zurich Aussersihl"
AUSSERSIHL_TILES_DIR := $(DATA_INTERIM_DIR)/aussersihl_tiles
AUSSERSIHL_INTERSECTING_TILES_CSV = $(AUSSERSIHL_TILES_DIR)/intersecting_tiles.csv
AUSSERSIHL_TILES_CSV := $(AUSSERSIHL_TILES_DIR)/tiles.csv
#### code
MAKE_LULC_RASTER_PY := $(CODE_DIR)/make_lulc_raster.py

### rules
$(AUSSERSIHL_TILES_DIR): | $(DATA_INTERIM_DIR)
	mkdir $@
$(AUSSERSIHL_INTERSECTING_TILES_CSV): $(GET_TILES_TO_DOWNLOAD_PY) $(ORTHOIMG_SHP) \
	| $(AUSSERSIHL_TILES_DIR)
	python $(GET_TILES_TO_DOWNLOAD_PY) $(ORTHOIMG_SHP) \
		$(AUSSERSIHL_NOMINATIM_QUERY) $@ --op intersects
$(AUSSERSIHL_TILES_CSV): $(AUSSERSIHL_INTERSECTING_TILES_CSV) $(MAKE_TILES_PY) \
	| $(AUSSERSIHL_TILES_DIR)
	python $(MAKE_TILES_PY) $< $(AUSSERSIHL_TILES_DIR) $@ \
		--nominatim-query $(AUSSERSIHL_NOMINATIM_QUERY) \
		--exclude-nominatim-query "Lake Zurich" --keep-raw
aussersihl_tiles: $(AUSSERSIHL_TILES_CSV)


# notebooks (for CI)

NOTEBOOKS_DIR = notebooks
OUTPUT_DIR := $(NOTEBOOKS_DIR)/output

$(OUTPUT_DIR):
	mkdir $(OUTPUT_DIR)

execute_notebooks: | $(OUTPUT_DIR)
	jupyter nbconvert --ExecutePreprocessor.timeout=5000 --to notebook \
		--execute $(NOTEBOOKS_DIR)/*.ipynb --output-dir $(OUTPUT_DIR)
	rm -rf $(OUTPUT_DIR)

#################################################################################

.DEFAULT_GOAL := help

# Inspired by <http://marmelab.com/blog/2016/02/29/auto-documented-makefile.html>
# sed script explained:
# /^##/:
# 	* save line in hold space
# 	* purge line
# 	* Loop:
# 		* append newline + line to hold space
# 		* go to next line
# 		* if line starts with doc comment, strip comment character off and loop
# 	* remove target prerequisites
# 	* append hold space (+ newline) to line
# 	* replace newline plus comments by `---`
# 	* print line
# Separate expressions are necessary because labels cannot be delimited by
# semicolon; see <http://stackoverflow.com/a/11799865/1968>
.PHONY: help
help:
	@echo "$$(tput bold)Available rules:$$(tput sgr0)"
	@echo
	@sed -n -e "/^## / { \
		h; \
		s/.*//; \
		:doc" \
		-e "H; \
		n; \
		s/^## //; \
		t doc" \
		-e "s/:.*//; \
		G; \
		s/\\n## /---/; \
		s/\\n/ /g; \
		p; \
	}" ${MAKEFILE_LIST} \
	| LC_ALL='C' sort --ignore-case \
	| awk -F '---' \
		-v ncol=$$(tput cols) \
		-v indent=19 \
		-v col_on="$$(tput setaf 6)" \
		-v col_off="$$(tput sgr0)" \
	'{ \
		printf "%s%*s%s ", col_on, -indent, $$1, col_off; \
		n = split($$2, words, " "); \
		line_length = ncol - indent; \
		for (i = 1; i <= n; i++) { \
			line_length -= length(words[i]) + 1; \
			if (line_length <= 0) { \
				line_length = ncol - indent - length(words[i]) - 1; \
				printf "\n%*s ", -indent, " "; \
			} \
			printf "%s ", words[i]; \
		} \
		printf "\n"; \
	}' \
	| more $(shell test $(shell uname) = Darwin && echo '--no-init --raw-control-chars')
