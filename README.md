# WRT-API

The Weather Routing API is a REST API for the [Weather Routing Tool](https://github.com/52North/WeatherRoutingTool).

This repository contains a local test setup of the Weather Routing API with [kind](https://kind.sigs.k8s.io/).

The API is based on the [OGC API Processes standard](https://docs.ogc.org/is/18-062r2/18-062r2.html) and runs with [pygeoapi](https://github.com/geopython/pygeoapi) and a custom [pygeoapi kubernetes job manager](https://github.com/52North/pygeoapi_k8s-manager).

To store process job results, the S3-compatible object store [Alarik](https://alarik.io/) is used. Please note that Alarik is currently in **Alpha**.

The following sections provide step-by-step instructions on how to deploy a local test version with kind.

## Install required tools

- Kind: https://kind.sigs.k8s.io/docs/user/quick-start/#installation
- Kubectl: https://kubernetes.io/docs/tasks/tools/#kubectl
- Docker: https://docs.docker.com/engine/install/ (alternatively [Podman](https://podman.io/))

## Create Kubernetes cluster

Create cluster:

```shell
kind create cluster --config k8s/kind-cluster.yaml
```

**Important**: Be sure to use a compatible version for your kind cluster. Versions between client (kubectl) and server (kind) are only allowed to differ in minor version of +/-1. The kind version is defined in `kind-cluster.yaml` via the image tag. The kubectl version can be checked with `kubectl version`.

Check cluster:

```shell
kubectl cluster-info --context kind-wrt-api
```

## Prepare Docker Images

**Important**: if you want to make sure that kind is using your image from the local registry, do not use the "latest" tag. Otherwise, it might try to pull the image from a remote registry.

### Weather Routing Tool

Currently, there is no public image of the Weather Routing API available on Docker Hub. 
Build the image locally in the directory `WRT-API/docker$`:

```shell
VERSION=local \
REGISTRY=docker.io \
IMAGE=52north/weather-routing-api \
; \
docker build \
  -t "${REGISTRY}/${IMAGE}:${VERSION}" \
  --build-arg VERSION="$VERSION" \
  --build-arg BUILD_DATE=$(date -u --iso-8601=seconds) \
  --build-arg GIT_COMMIT=$(git rev-parse --short=20 -q --verify HEAD) \
  --build-arg GIT_TAG=$(git describe --tags) \
  --build-arg GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD) \
  .
```

[Load docker image](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster) into kind cluster:

```shell
kind load docker-image --name wrt-api 52north/weather-routing-api:local
```

### Pygeoapi

The latest image of the pygeoapi-k8s-manager enabled pygeoapi is available on Docker Hub. Kind will pull the image automatically
if the tag "latest" is used in the k8s manifest `manager.yaml` (default).

Alternatively, the image can be built locally, see the instructions [outlined in the documentation](https://github.com/52North/pygeoapi_k8s-manager/blob/main/README.md#container).

If a different tag than "latest" is used, [load docker image](https://kind.sigs.k8s.io/docs/user/quick-start/#loading-an-image-into-your-cluster) into kind cluster with the correct tag; here we assume its "local":

```shell
kind load docker-image --name wrt-api 52north/pygeoapi-k8s-manager:local
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

## Copernicus credentials

This step can be skipped if `"wrt_algorithm_type": "gcr_slider"` is used as process input. This is the recommended setting for quick tests.

If you don't have a Copernicus Marine Service account yet, register at https://marine.copernicus.eu/.

Create a secret `.secrets.cmems` file to be used during secret creation to not leak information in the shell history:

```ini
user=
password=
```

Create the secret with the following command:

```shell
kubectl create secret generic cmems-credentials --from-env-file=.secrets.cmems
```

Verify the secret (debugging):

```shell
echo "User: '$(kubectl get secrets cmems-credentials --template='{{ index .data "user" }}' | base64 -d)'" && \
echo "Password: '$(kubectl get secrets cmems-credentials --template='{{ index .data "password" }}' | base64 -d)'"
```

## Run containers

Apply k8s manifests:

```shell
WRT-API/k8s$ kubectl apply -k .
```

Check k8s resources (for debugging):

```shell
WRT-API/k8s$ kubectl get all
```

## Test application

Pygeoapi is running at <http://localhost:30080/pygeoapi/>.

Alarik is running at <http://localhost:30100/>.

### Execute process

Execute the "weather routing tool" process **asynchronously**:

```shell
curl -v -X 'POST' \
  'http://localhost:30080/pygeoapi/processes/weather-routing-tool/execution' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -H 'Prefer: respond-async' \
  -d '{
        "inputs": {
          "wrt_departure_time": "2026-03-06T12:00Z"
          "wrt_default_route": [53.55, 0.16, 52.0, 4.0]
          "wrt_default_map": [51.9, 0.0, 53.7, 4.3]
          "wrt_boat_speed": 6
          "wrt_algorithm_type": "gcr_slider"
          "wrt_contraints_list": ["land_crossing_global_land_mask", "on_map"]
        }
      }'
```

### Get process result

In the following command, substitute the job id (`d63f2052-193e-11f1-beea-4661ad013146`) with the actual id.

```shell
curl -v http://localhost:30080/pygeoapi/jobs/d63f2052-193e-11f1-beea-4661ad013146/results?f=json \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json'
```

This will return a link to the s3 output folder. From there the actual route can be downloaded:

1. Via UI:
   - Visit Alarik at <http://localhost:30100/> and login (default: alarik/alarik).
   - Navigate to the output folder and download the final route (`route_gcr_slider.geojson` if you use the example request).
2. Programmatically:
   - Alarik currently doesn't support public download urls (see https://github.com/achtungsoftware/alarik/issues/7).
   - Via shell and Alarik's internal API:
    ```shell
    curl -v -X 'POST' \
      'http://localhost:30090/api/v1/objects/download' \
      -H 'accept: application/json' \
      -H 'Content-Type: application/json' \
      -H 'X-Access-Key: wrt-key' \
      -H 'X-Secret-Key: wrt-secret' \
      -d '{
            "bucket": "wrt",
            "keys": ["k8s-job-manager/processes/weather-routing-tool/outputs/2026-03-06_d63f2052-193e-11f1-beea-4661ad013146/route_gcr_slider.geojson"]
         }'
    ```
   - Via Python and s3:
    ```python
    from s3fs import S3FileSystem
    
    s3 = S3FileSystem(endpoint_url="http://localhost:30090", key="wrt-key", secret="wrt-secret")
    # Substitute the string "2026-03-06_d63f2052-193e-11f1-beea-4661ad013146" path
    s3.get("wrt/k8s-job-manager/processes/weather-routing-tool/outputs/2026-03-06_d63f2052-193e-11f1-beea-4661ad013146/route_gcr_slider.geojson", "~/Downloads/route_gcr_slider.geojson")
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
