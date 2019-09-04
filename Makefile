.PHONY: tiles

#################################################################################

# globals

## variables
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

# tiles

## variables
### Swiss municipal boundaries https://bit.ly/2HewYJx
GMB_URI = https://www.bfs.admin.ch/bfsstatic/dam/assets/5247306/master
GMB_DIR := $(DATA_RAW_DIR)/gmb
GMB_BASENAME = g1a18
GMB_SHP := $(GMB_DIR)/$(GMB_BASENAME).shp

### Zurich orthofoto https://www.geolion.zh.ch/geodatensatz/2831
ORTHOIMG_URI_BASE = \
	https://maps.zh.ch/download/orthofoto/sommer/2014/rgb/jpeg/ortho_sommer14
ORTHOIMG_SHP_EXTENSIONS = dbf prj shx
ORTHOIMG_SHP_DIR := $(DATA_RAW_DIR)/orthoimg
ORTHOIMG_SHP_BASEPATH := $(ORTHOIMG_SHP_DIR)/ortho_sommer14
ORTHOIMG_SHP_OTHERS := $(foreach EXT, $(ORTHOIMG_SHP_EXTENSIONS), \
	$(ORTHOIMG_SHP_BASEPATH).$(EXT))
ORTHOIMG_SHP := $(ORTHOIMG_SHP_BASEPATH).shp

TILES_DIR = $(DATA_INTERIM_DIR)/tiles
GET_TILES_TO_DOWNLOAD_PY = src/get_tiles_to_download.py
MAKE_TILES_PY = src/make_tiles.py

INTERSECTING_TILES_CSV := $(TILES_DIR)/intersecting_tiles.csv
DOWNSCALED_TILES_CSV := $(TILES_DIR)/downscaled_tiles.csv

## rules
$(GMB_DIR): | $(DATA_RAW_DIR)
	mkdir $@
$(GMB_DIR)/%.zip: $(DOWNLOAD_URI_PY) | $(GMB_DIR)
	wget $(GMB_URI) -O $@
$(GMB_DIR)/%.shp: $(GMB_DIR)/%.zip
	unzip -j $< 'ggg_2018-LV95/shp/$(GMB_BASENAME)*' -d $(GMB_DIR)
	touch $@

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
	$(GMB_SHP) | $(TILES_DIR)
	python $(GET_TILES_TO_DOWNLOAD_PY) $(ORTHOIMG_SHP) $(GMB_SHP) $@
$(DOWNSCALED_TILES_CSV): $(INTERSECTING_TILES_CSV) $(ORTHOIMG_SHP) \
	$(MAKE_TILES_PY) | $(TILES_DIR)
	python $(MAKE_TILES_PY) $(INTERSECTING_TILES_CSV) $(TILES_DIR) $@
tiles: $(DOWNSCALED_TILES_CSV)

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
