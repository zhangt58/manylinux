export MANYLINUX_BUILD_FRONTEND=docker
build:
	PLATFORM=$(shell uname -m) POLICY=manylinux2014 COMMIT_SHA=latest ./build.sh
deploy:
	PLATFORM=$(shell uname -m) POLICY=manylinux2014 COMMIT_SHA=latest ./deploy.sh
