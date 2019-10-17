SOURCE=src/cisco_gnmi
TEST_DIR=tests

.PHONY: clean
clean:
	rm -rf .coverage htmlcov/

.PHONY: install
install:
	pip install --upgrade pip
	pip install -r $(TEST_DIR)/requirements.txt
	pip install .

.PHONY: test
test: clean
	pytest $(TEST_DIR) -v --disable-warnings

.PHONY: open-report
open-report:
	pytest --cov=src/ --cov-report=term-missing --cov-report=html --disable-warnings
	open htmlcov/index.html || xdg-open htmlcov/index.html
