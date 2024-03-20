# VERSION defines the project version for the bundle.
VERSION ?= main

# In CI, to be replaced by `netobserv`
IMAGE_ORG ?= $(USER)

# IMAGE_TAG_BASE defines the namespace and part of the image name for remote images.
IMAGE_TAG_BASE ?= quay.io/$(IMAGE_ORG)/netobserv-ai

# Image URL to use all building/pushing image targets
IMAGE ?= $(IMAGE_TAG_BASE):$(VERSION)

NAMESPACE ?= netobserv

# Image building tool (docker / podman) - docker is preferred in CI
OCI_BIN_PATH = $(shell which docker 2>/dev/null || which podman)
OCI_BIN ?= $(shell basename ${OCI_BIN_PATH})

.PHONY: image-build
image-build:
	$(OCI_BIN) build --build-arg BUILD_VERSION="${BUILD_VERSION}" -t ${IMAGE} .

.PHONY: image-push
image-push:
	$(OCI_BIN) push ${IMAGE}

.PHONY: images
images: image-build image-push ## Build and push images

.PHONY: deploy
deploy:
	sed 's|%DOCKER_IMG%|$(IMAGE)|g' deploy.yaml > /tmp/deployment.yaml
	kubectl apply -f /tmp/deployment.yaml -n "${NAMESPACE}"

.PHONY: undeploy
undeploy:
	sed 's|%DOCKER_IMG%|$(IMAGE)|g' deploy.yaml > /tmp/deployment.yaml
	kubectl delete -f /tmp/deployment.yaml -n "${NAMESPACE}"