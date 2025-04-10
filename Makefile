export MANYLINUX_BUILD_FRONTEND=docker

build:
	PLATFORM=$(shell uname -m) POLICY=manylinux2014 COMMIT_SHA=shared ./build.sh

deploy:
	PLATFORM=$(shell uname -m) POLICY=manylinux2014 COMMIT_SHA=shared ./deploy.sh

deploy-test:
	PLATFORM=$(shell uname -m) POLICY=manylinux2014 COMMIT_SHA=shared ./deploy.sh --dry-run

.PHONY: build deploy deploy-test
