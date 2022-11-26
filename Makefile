# Makefile acting as script repo

VIRTUALENV_DIR			:=	.venv

PIP_TOOLS				:=	$(VIRTUALENV_DIR)/bin/python -Wignore::UserWarning:_distutils_hack -m piptools

PIP_COMPILE_FLAGS		=	--no-allow-unsafe --resolver=backtracking --quiet

PIP_COMPILE				:=	$(PIP_TOOLS) compile

PIP_SYNC_FLAGS			=

PIP_SYNC				:=	$(PIP_TOOLS) sync

REQUIREMENTS_FILES		=	requirements.txt		\
							requirements-dev.txt	\
							requirements-test.txt


all:	repo

repo:	pip-sync
	$(VIRTUALENV_DIR)/bin/pre-commit install
	@echo "Activate your new virtual env which is $(VIRTUALENV_DIR)"

pip-sync:	$(VIRTUALENV_DIR)
	$(PIP_SYNC) $(PIP_SYNC_FLAGS) $(REQUIREMENTS_FILES)

pip-compile:	$(REQUIREMENTS_FILES)

pip-upgrade:	PIP_COMPILE_FLAGS += --upgrade
pip-upgrade:	pip-compile pip-sync

requirements.txt:	FORCE
	$(PIP_COMPILE) $(PIP_COMPILE_FLAGS) --output-file=$@ pyproject.toml

requirements-%.txt:	FORCE
	$(PIP_COMPILE) $(PIP_COMPILE_FLAGS) --extra=$* --output-file=$@ pyproject.toml

FORCE:

$(VIRTUALENV_DIR):
	python3 -m venv $@
	$@/bin/python -m pip install --upgrade pip
	$@/bin/pip install pip-tools $(addprefix -r, $(REQUIREMENTS_FILES))


.PHONY: all repo pip-compile pip-sync pip-update pip-upgrade FORCE