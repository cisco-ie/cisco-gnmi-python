TEST_DIR=tests

## Sets up the virtual environment via pipenv.
.PHONY: setup
setup:
	pipenv --three install --dev

## Cleans test and packaging outputs.
.PHONY: clean
clean:
	rm -rf .coverage build/ dist/

## Runs tests.
.PHONY: test
test: clean
	pipenv run pytest $(TEST_DIR) -v -s --disable-warnings

## Creates coverage report.
.PHONY: coverage
coverage:
	pipenv run pytest --cov=src/ --cov-report=term-missing --disable-warnings

.DEFAULT:
	@$(MAKE) help

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