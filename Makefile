PYTHON3      = python3
SOURCEDIR    = pyp4
TESTDIR      = tests
COVREP       = term
MINCOV       = 0

help:
	@echo "test-deps         Install the package test and lint requirements."
	@echo "tests             Run the tests."
	@echo "examples          Run all the examples."
	@echo "coverage          Print the coverage report."
	@echo "flake8            Run the flake8 linter."
	@echo "pylint            Run the pylint linter."
	@echo "cov-html          Open the coverage report produced using `make tests COVREP=html`."
	@echo "clean             Removes all temporary files (such as .pyc and __pycache__)."
	@echo "verify            Verify the installation by running tests and linters."
	@echo "install           Install the package (editable)."
	@echo "bdist             Builds the package."
	@echo "deploy-bdist      Builds and uploads the package to the pypi server."

test-deps:
	@$(PYTHON3) -m pip install --upgrade -r test_requirements.txt

tests:
	@$(PYTHON3) -m pytest -v --cov=${SOURCEDIR} --cov-report=${COVREP} tests

examples:
	@$(PYTHON3) -m examples.run_examples > /dev/null && echo "Examples OK!" || (echo "Examples failed!" && /bin/false)

coverage:
	@$(PYTHON3) -m coverage report --fail-under=${MINCOV}

flake8:
	@$(PYTHON3) -m flake8 ${SOURCEDIR} ${TESTDIR}

pylint:
	@$(PYTHON3) -m pylint ${SOURCEDIR} ${TESTDIR}

cov-html:
	xdg-open htmlcov/index.html

clean:
	@/usr/bin/find . -name '*.pyc' -delete
	@/usr/bin/rm -f .coverage
	@/usr/bin/find . -name __pycache__ -prune -exec rm -rf "{}" \;
	@/usr/bin/rm -rf htmlcov

verify: clean test-deps tests flake8 pylint _verified

_verified:
	@echo "The package has been successfully verified :)"

# TODO: Leave commented while under development

# install: _check_variables test-deps
# 	@$(PYTHON3) -m pip install -e .

# _clean_dist:
# 	@/bin/rm -rf dist

# bdist:
# 	@$(PYTHON3) setup.py bdist_wheel

# deploy-bdist: _clean_dist bdist
# 	@$(PYTHON3) setup.py deploy

.PHONY: test-deps tests examples coverage flake8 pylint cov-html clean verify _verified install _clean_dist bdist deploy-bdist
