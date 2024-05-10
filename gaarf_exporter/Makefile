SHELL=/bin/bash
PYTHON=`which python`

.PHONY: build

tests-e2e:
	@echo "Runing end-to-end tests"
	@${PYTHON} `which pytest` -m 'not slow' tests/end-to-end/

tests-slow:
	@echo "Runing slow end-to-end tests"
	@${PYTHON} `which pytest` -m 'slow' tests/end-to-end/

build:
	DOCKER_BUILDKIT=1 docker build -t gaarf-exporter .

force_build:
	DOCKER_BUILDKIT=1 docker build -t gaarf-exporter --no-cache .

clean:
	@echo "Removing the build/ dist/ and *.egg-info/ directories"
	@rm -rf build dist *.egg-info

upload:
	@echo "Uploading built package to PyPI"
	@${PYTHON} `which twine` upload dist/*

bundle:
	@echo "Bundling the code"; echo
	@${PYTHON} setup.py sdist bdist_wheel

upload_pypi: | clean bundle upload
