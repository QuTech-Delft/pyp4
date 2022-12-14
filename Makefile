PYTHON       = python3
SOURCEDIR    = pyp4
TESTDIR      = tests
COVREP       = term
MINCOV       = 100

help:
	@echo "dependencies      Install the package dependencies."
	@echo "dependencies.dev  Install additional package dependencies for development."
	@echo "dependencies.docs Install additional package dependencies for documentation."
	@echo "examples          Run the examples."
	@echo "tests             Run the tests."
	@echo "coverage          Print the coverage report."
	@echo "cov-html          Open the coverage report produced by 'make tests COVREP=html'."
	@echo "flake8            Run the flake8 linter."
	@echo "pylint            Run the pylint linter."
	@echo "clean             Remove all temporary files."
	@echo "distclean         Remove all temporary and build files."
	@echo "verify            Verify the project by running tests and linters."

dependencies:
	@$(PYTHON) -m pip install --upgrade -e .

dependencies.dev:
	@$(PYTHON) -m pip install --upgrade -e .[dev]

dependencies.docs:
	@$(PYTHON) -m pip install --upgrade -e .[docs]

examples:
	@$(PYTHON) -m examples.run_examples > /dev/null && echo "Examples OK!" || \
	(echo "Examples failed!" && /bin/false)

tests:
	@$(PYTHON) -m pytest -v --cov=${SOURCEDIR} --cov-report=${COVREP} ${TESTDIR}

coverage:
	@$(PYTHON) -m coverage report --fail-under=${MINCOV}

cov-html:
	@xdg-open htmlcov/index.html

flake8:
	@$(PYTHON) -m flake8 ${SOURCEDIR} ${TESTDIR}

pylint:
	@$(PYTHON) -m pylint ${SOURCEDIR}

clean:
	@/usr/bin/find . -name '*.pyc' -delete
	@/usr/bin/find . -name __pycache__ -prune -exec rm -rf "{}" \;
	@/usr/bin/rm -rf .pytest_cache
	@/usr/bin/rm -f .coverage
	@/usr/bin/rm -rf htmlcov

distclean: clean
	@/usr/bin/rm -rf *.egg-info
	@/usr/bin/rm -rf build
	@/usr/bin/rm -rf dist

_verified:
	@echo "The package has been successfully verified"

verify: clean dependencies dependencies.dev tests examples coverage flake8 pylint _verified

build: distclean verify
	@$(PYTHON) -m build

.PHONY: dependencies dependencies.dev dependencies.docs examples tests coverage cov-html flake8 \
	pylint clean distclean verify _verified
