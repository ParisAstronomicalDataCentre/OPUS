WWWUSER ?= www
VAR_PATH ?= var_data

init:
	mkdir -p $(VAR_PATH)/config
	mkdir -p $(VAR_PATH)/db
	mkdir -p $(VAR_PATH)/jdl
	mkdir -p $(VAR_PATH)/jdl/scripts
	mkdir -p $(VAR_PATH)/jdl/scripts/new
	mkdir -p $(VAR_PATH)/jdl/scripts/saved
	mkdir -p $(VAR_PATH)/jdl/votable
	mkdir -p $(VAR_PATH)/jdl/votable/new
	mkdir -p $(VAR_PATH)/jdl/votable/saved
	mkdir -p $(VAR_PATH)/jobdata
	mkdir -p $(VAR_PATH)/logs
	mkdir -p $(VAR_PATH)/results
	mkdir -p $(VAR_PATH)/temp
	mkdir -p $(VAR_PATH)/uploads
	mkdir -p $(VAR_PATH)/workdir
	chown -R $(WWWUSER) $(VAR_PATH)

test:
	pytest -s

