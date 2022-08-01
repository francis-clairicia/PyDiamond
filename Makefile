# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
# Makefile acting as script database

export SOURCE_DATE_EPOCH	=	$(shell git log -1 --pretty=%ct)

SRC							=	./

DISTRIB_DIRECTORY			=	./dist

PROJECT_CONFIG				=	./pyproject.toml

MYPY_CACHE					=	./.mypy_cache

PYTEST_CACHE				=	./.pytest_cache

all:	build

build:	BLACK_ARGS += --check --diff --quiet
build:	ISORT_ARGS += --check --diff --quiet
build:	PYTEST_ARGS += --quiet --exitfirst
build:	pre-build lint format test
	@echo "Using SOURCE_DATE_EPOCH=$(SOURCE_DATE_EPOCH)"
	flit build

pre-build:
	@if [[ "$(shell git status --porcelain)" ]]; then echo "Please commit/stash your changes before."; git status --porcelain; exit 1; fi

lint:
	mypy --non-interactive --install-types --config-file=$(PROJECT_CONFIG) $(MYPY_ARGS) $(SRC)

format:
	isort --settings-file=$(PROJECT_CONFIG) $(ISORT_ARGS) $(SRC)
	black --config=$(PROJECT_CONFIG) $(BLACK_ARGS) $(SRC)

test:
	pytest -c $(PROJECT_CONFIG) $(PYTEST_ARGS)

fclean:
	$(RM) -r $(DISTRIB_DIRECTORY)
	$(RM) -r $(MYPY_CACHE)
	$(RM) -r $(PYTEST_CACHE)

.PHONY: all build pre-build lint format test fclean
