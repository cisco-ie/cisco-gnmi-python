TEST_DIR=tests
#PYPI_URL=https://test.pypi.org/legacy/
PYPI_URL=https://upload.pypi.org/legacy/
DEFAULT_PYTHON_VERSION=three

## Sets up the virtual environment via pipenv.
.PHONY: setup
setup:
	pipenv --$(DEFAULT_PYTHON_VERSION) install --dev

## Removes everything including virtual environments.
.PHONY: clean
clean: mostlyclean
	-pipenv --rm
	rm -f Pipfile.lock

## Removes test and packaging outputs.
.PHONY: mostlyclean
mostlyclean:
	rm -rf .coverage htmlcov/ .pytest_cache/ build/ dist/

## Runs tests.
.PHONY: test
test:
	pipenv run pytest $(TEST_DIR) -v -s --disable-warnings

## Creates coverage report.
.PHONY: coverage
coverage:
	pipenv run pytest --cov=src/ --cov-report=term-missing --cov-report=html --disable-warnings
	open htmlcov/index.html || xdg-open htmlcov/index.html

## Packages for both Python 2 and 3 for PyPi.
.PHONY: dist
dist: mostlyclean
	-pipenv --rm
	pipenv --three install --dev --skip-lock
	pipenv run python setup.py sdist bdist_wheel
	pipenv --rm
	pipenv --two install --dev --skip-lock
	pipenv run python setup.py sdist bdist_wheel
	pipenv --rm
	pipenv --$(DEFAULT_PYTHON_VERSION) install --dev

## Uploads packages to PyPi.
.PHONY: upload
upload:
	pipenv run twine upload --repository-url $(PYPI_URL) dist/*

## Alias for packaging and upload together.
.PHONY: pypi
pypi: dist upload

## This help message.
.PHONY: help
help:
	@printf "\nUsage:\n";

	@awk '{ \
			if ($$0 ~ /^.PHONY: [a-zA-Z\-\_0-9]+$$/) { \
				helpCommand = substr($$0, index($$0, ":") + 2); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^[a-zA-Z\-\_0-9.]+:/) { \
				helpCommand = substr($$0, 0, index($$0, ":")); \
				if (helpMessage) { \
					printf "\033[36m%-20s\033[0m %s\n", \
						helpCommand, helpMessage; \
					helpMessage = ""; \
				} \
			} else if ($$0 ~ /^##/) { \
				if (helpMessage) { \
					helpMessage = helpMessage"\n                     "substr($$0, 3); \
				} else { \
					helpMessage = substr($$0, 3); \
				} \
			} else { \
				if (helpMessage) { \
					print "\n                     "helpMessage"\n" \
				} \
				helpMessage = ""; \
			} \
		}' \
		$(MAKEFILE_LIST)

## Setup links in virtual env for development
develop:
	@echo "--------------------------------------------------------------------"
	@echo "Setting up development environment"
	@python setup.py develop --no-deps -q
	@echo ""
	@echo "Done."
	@echo ""

## Remove development links in virtual env
undevelop:
	@echo "--------------------------------------------------------------------"
	@echo "Removing development environment"
	@python setup.py develop --no-deps -q --uninstall
	@echo ""
	@echo "Done."
	@echo ""