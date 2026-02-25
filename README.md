# WRT-API

The Weather Routing API is a REST API for the [Weather Routing Tool](https://github.com/52North/WeatherRoutingTool).

This repository contains a local test setup of the Weather Routing API with [kind](https://kind.sigs.k8s.io/).

The API is based on the [OGC API Processes standard](https://docs.ogc.org/is/18-062r2/18-062r2.html) and runs with [pygeoapi](https://github.com/geopython/pygeoapi).

The following sections provide step-by-step instructions on how to deploy a local test version with kind.

## Install required tools

- Kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
- Kubectl: https://kubernetes.io/docs/tasks/tools/#kubectl
- Docker: https://docs.docker.com/engine/install/ (alternatively [Podman](https://podman.io/))

## Create Kubernetes cluster

Create cluster:

```shell
kind create cluster --config kind-cluster.yaml
```

**Important**: Be sure to use a compatible version for your kind cluster. Versions between client (kubectl) and server (kind) are only allowed to differ in minor version of +/-1. The kind version is defined in `kind-cluster.yaml` via the image tag. The kubectl version can be checked with `kubectl version`.

Check cluster:

```shell
kubectl cluster-info --context kind-wrt-api
```

## Prepare Docker Images

### Pygeoapi

The latest image of the pygeoapi-k8s-manager enabled pygeoapi can be pulled from Docker Hub:

```shell
docker pull 52north/pygeoapi-k8s-manager
```

Alternatively, the  image can be built locally, see the instructions [outlined in the documentation](https://github.com/52North/pygeoapi_k8s-manager/blob/main/README.md#container). You might want to use a different tag for local testing, e.g. set `VERSION` to `local`. In this case, the tag has to be updated in the following command.

[Load docker image](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster) into kind cluster:

```shell
kind load docker-image --name wrt-api 52north/pygeoapi-k8s-manager:latest
```

### Weather Routing Tool

The latest image of the Weather Routing Tool can be pulled from Docker Hub (not yet supported):

ToDo: add shell command after uploading the image to Docker Hub.

Alternatively, the  image can be built locally, see instructions [outlined in the documentation](https://52north.github.io/WeatherRoutingTool/).

[Load docker image](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster) into kind cluster:

```shell
kind load docker-image --name wrt-api 52north/weather-routing-tool:latest
```

### Kind image management (for debugging)

Check available images:

```shell
docker exec -it wrt-api-control-plane crictl images
```

Delete image:

```shell
docker exec -it wrt-api-control-plane crictl rmi <id>
```

## Run containers

Apply k8s manifests:

```shell
WRT-API/$ kubectl apply -k .
```

Check k8s resources (for debugging):

```shell
WRT-API/$ kubectl get all
```

## Test application

Visit pygeoapi at <http://localhost:30080/pygeoapi/>

Execute the "hello world" process **synchronous**:

```shell
curl -v -X 'POST' \
  'http://localhost:30080/pygeoapi/processes/hello-world-k8s/execution' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
        "inputs": {
          "message": "Am I in TV, now?",
          "name": "John Doe"
        }
      }'
```

or **asynchronous**:

```shell
curl -v -X 'POST' \
  'http://localhost:30080/pygeoapi/processes/hello-world-k8s/execution' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Prefer: respond-async' \
  -d '{
        "inputs": {
          "message": "Am I in TV, now?",
          "name": "John Doe"
        }
      }'
```

## Remove cluster

Execute the following command to clean up the cluster and its configuration:

```shell
kind delete cluster --name kind-wrt-api
```

## Funding

|                                                               Project/Logo                                                                | Description                                                                                                                                                                                                                                                                                 |
|:-----------------------------------------------------------------------------------------------------------------------------------------:|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [<img alt="TwinShip" align="middle" src="https://github.com/52North/WRT-API/blob/main/images/twinship_logo.png"/>](https://twin-ship.eu/) | Co-funded by the European Union’s Horizon Europe programme under grant agreement No. 101192583                                                                                                                                                                                              |
