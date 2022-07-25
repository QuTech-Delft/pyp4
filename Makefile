PYTHON       = python3
SOURCEDIR    = pyp4
TESTDIR      = tests
COVREP       = term
MINCOV       = 0

help:
	@echo "dev-requirements  Install extra requirements for development."
	@echo "examples          Run all the examples."
	@echo "tests             Run the tests."
	@echo "coverage          Print the coverage report."
	@echo "cov-html          Open the coverage report produced using `make tests COVREP=html`."
	@echo "flake8            Run the flake8 linter."
	@echo "pylint            Run the pylint linter."
	@echo "clean             Removes all temporary files (such as .pyc and __pycache__)."
	@echo "verify            Verify the project by running tests and linters."

dev-requirements:
	@$(PYTHON) -m pip install --upgrade -r dev-requirements.txt

examples:
	@$(PYTHON) -m examples.run_examples > /dev/null && echo "Examples OK!" || (echo "Examples failed!" && /bin/false)

tests:
	@$(PYTHON) -m pytest -v --cov=${SOURCEDIR} --cov-report=${COVREP} ${TESTDIR}

coverage:
	@$(PYTHON) -m coverage report --fail-under=${MINCOV}

cov-html:
	xdg-open htmlcov/index.html

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

_verified:
	@echo "The package has been successfully verified"

verify: clean dev-requirements tests coverage flake8 pylint _verified

.PHONY: dev-requirements examples tests coverage cov-html flake8 pylint clean verify _verified
