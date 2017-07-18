WWWUSER ?= www
VAR_PATH ?= var_data

init:
	mkdir -p $(VAR_PATH)/db
	mkdir -p $(VAR_PATH)/jdl
	mkdir -p $(VAR_PATH)/jdl/scripts
	mkdir -p $(VAR_PATH)/jdl/wadl
	mkdir -p $(VAR_PATH)/jdl/votable
	mkdir -p $(VAR_PATH)/jobdata
	mkdir -p $(VAR_PATH)/logs
	mkdir -p $(VAR_PATH)/temp
	mkdir -p $(VAR_PATH)/uploads
	mkdir -p $(VAR_PATH)/workdir
	chown -R $(WWWUSER) $(VAR_PATH)/*

test:
	./test.py
