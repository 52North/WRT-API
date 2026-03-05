import json
import logging
import os
import pathlib
from datetime import datetime

from s3fs import S3FileSystem

from WeatherRoutingTool.config import Config, set_up_logging
from WeatherRoutingTool.execute_routing import execute_routing
from WeatherRoutingTool.ship.ship_config import ShipConfig

# Necessary to avoid writing checksums into files when uploading them to the bucket (cf. https://github.com/boto/boto3/issues/4435)
os.environ["AWS_REQUEST_CHECKSUM_CALCULATION"] = "when_required"
os.environ["AWS_RESPONSE_CHECKSUM_VALIDATION"] = "when_required"

logger = logging.getLogger('WRT.API')


def extract_params_from_process_inputs(inputs: dict = None):
    wrt_config_params = {}
    for k, v in inputs.items():
        if isinstance(k, str):
            if k.lower().startswith("wrt_"):
                param = k.lower().removeprefix("wrt_").upper()
                wrt_config_params[param] = v
    return wrt_config_params


def upload_folder_to_s3_bucket(
    local_path: str, bucket_path: str, endpoint_url: str, key: str, secret: str, anon: str = False
):
    """
    Upload a folder to an S3 bucket.

    :param local_path: use "<folder>/*" to copy only the content of the folder not the folder itself
    :type local_path: str
    :param bucket_path:
    :type bucket_path: str
    :param endpoint_url:
    :type endpoint_url: str
    :param key:
    :type key: str
    :param secret:
    :type secret: str
    :param anon:
    :type anon: bool
    :return:
    """
    logger.info(
        f"Start uploading outputs from '{local_path}' to '{endpoint_url}/{bucket_path}'"
    )
    files = [file for file in pathlib.Path(local_path).rglob("*") if file.is_file()]
    idx = 1
    count = len(files)
    logger.info(f"Start Uploading {count} files")
    s3 = S3FileSystem(endpoint_url=endpoint_url, key=key, secret=secret, anon=anon)
    for file in files:
        destination = f"{bucket_path}{file.name}"
        print(f"[{idx}/{count}] Uploading {file.name}")
        s3.put(str(file), destination)
        idx += 1
    logger.info(f"Finished uploading {count} files")


def handle_outputs(pygeoapi_process_id, pygeoapi_job_id) -> str:
    outputs_bucket_endpoint = os.getenv("PROCESS_OUTPUTS_BUCKET_ENDPOINT")
    outputs_bucket_key = os.getenv("PROCESS_OUTPUTS_BUCKET_KEY")
    outputs_bucket_secret = os.getenv("PROCESS_OUTPUTS_BUCKET_SECRET")
    outputs_bucket_name = os.getenv("PROCESS_OUTPUTS_BUCKET_NAME")
    outputs_bucket_path_prefix = os.getenv("PROCESS_OUTPUTS_BUCKET_PATH_PREFIX")
    outputs_local_path_prefix = os.getenv("PROCESS_OUTPUTS_LOCAL_PATH_PREFIX")

    outputs_bucket_full_path = f"{outputs_bucket_name}/{outputs_bucket_path_prefix}{pygeoapi_process_id}/outputs/{datetime.now().strftime('%Y-%m-%d')}_{pygeoapi_job_id}/"
    upload_folder_to_s3_bucket(
        outputs_local_path_prefix,
        outputs_bucket_full_path,
        outputs_bucket_endpoint,
        outputs_bucket_key,
        outputs_bucket_secret,
    )
    return f"{outputs_bucket_endpoint}/{outputs_bucket_full_path}"


def main():
    start = datetime.now()
    pygeoapi_job_id = os.getenv("PYGEOAPI_JOB_ID", "JOB_ID_NOT_FOUND")
    pygeoapi_process_id = os.getenv("PYGEOAPI_PROCESS_ID", "PROCESS_ID_NOT_FOUND")
    logger.info(f"Start Weather Routing Tool for job '{pygeoapi_job_id}'")

    # Process input
    input_str = os.getenv("PYGEOAPI_K8S_MANAGER_INPUTS")
    try:
        input_dict = json.loads(input_str)
    except json.JSONDecodeError as err:
        logger.error(f"Could not parse process inputs '{input_str}'. Error: '{err}'")
        raise
    except Exception as err:
        logger.error(f"Could not parse process inputs '{input_str}'. Error: '{err}'")
        raise

    # Extract config params from process input
    input_config = extract_params_from_process_inputs(input_dict)

    # WRT config
    config_dict = {
        "DEPTH_DATA": "/app/workdir/depth.nc",
        "WEATHER_DATA": "/app/workdir/weather.nc",
        "ROUTE_PATH": "/app/workdir",
    }
    config_dict = config_dict | input_config
    config = Config.validate_config(config_dict)
    debug = False
    info_log_file = "/app/workdir/info.log"
    set_up_logging(info_log_file, debug=debug)

    # Ship config
    ship_config_dict = {
        "DEPTH_DATA": "/app/workdir/depth.nc",
        "WEATHER_DATA": "/app/workdir/weather.nc",
        "ROUTE_PATH": "/app/workdir",
        "BOAT_SMCR_POWER": 6502,
        "BOAT_SMCR_SPEED": 7,
        "BOAT_FUEL_RATE": 167,
        "BOAT_DRAUGHT_AFT": 10,
        "BOAT_DRAUGHT_FORE": 10,
        "BOAT_LENGTH": 180,
        "BOAT_BREADTH": 32,
        "BOAT_HBR": 30,
        "BOAT_AXV": 716,
        "BOAT_AYV": 1910,
        "BOAT_AOD": 529,
        "BOAT_CMC": 8.1,
        "BOAT_HC": 7.06
    }
    ship_config_dict = ship_config_dict | input_config
    ship_config = ShipConfig.validate_config(ship_config_dict)

    # Run WRT
    execute_routing(config, ship_config)

    # Upload results to S3 bucket
    output_target = handle_outputs(pygeoapi_process_id, pygeoapi_job_id)

    logger.info(f"Finished Weather Routing Tool for job '{pygeoapi_job_id}'")
    logger.info("---------------------------")
    logger.info(f"Overall runtime : {(datetime.now() - start).total_seconds():8.3f}s")
    logger.info("PYGEOAPI_K8S_MANAGER_RESULT_MIMETYPE:application/json")
    process_id = os.getenv("PYGEOAPI_PROCESS_ID", "process-id-not-defined-in-env")
    logger.info(
        f'PYGEOAPI_K8S_MANAGER_RESULT_START\n{{"id":"{process_id}","value":"{output_target}"}}'
    )


if __name__ == "__main__":
    main()
