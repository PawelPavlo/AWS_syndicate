import decimal
import json
import uuid

import requests
import boto3
from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all

from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger('Processor-handler')
patch_all()

class OpenMeteoAPI:

    def __init__(self) -> None:
        self.url = "https://api.open-meteo.com/v1/forecast"

    def get_weather_forecast(self, latitude: float, longitude: float) -> dict: 
        
        response = requests.get(
            url=self.url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "hourly": "temperature_2m"
            }
        )
        response.raise_for_status()
        forecast = response.json()
        return forecast


open_meteo_api = OpenMeteoAPI()
PREFIX = "cmtr-b5eedb66-"
SUFFIX = "-test"
TABLE_NAME = f"{PREFIX}Weather{SUFFIX}"
weather_table = boto3.resource("dynamodb").Table(TABLE_NAME)


class Processor(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass
        
    def handle_request(self, event, context):

        try:
            forecast = open_meteo_api.get_weather_forecast(latitude=52.52, longitude=13.41)
        except Exception as e:
            _LOG.error(f"Failed to get weather forecast: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed to get weather forecast"})
            }

        try:
            item = {
                "id": str(uuid.uuid4()),
                "forecast": {
                    "elevation" : decimal.Decimal(str(forecast["elevation"])),
                    "generationtime_ms" : decimal.Decimal(str(forecast["generationtime_ms"])),
                    "hourly": {
                        "temperature_2m": [decimal.Decimal(str(temp)) for temp in forecast["hourly"]["temperature_2m"]],
                        "time": forecast["hourly"]["time"]
                    },
                    "hourly_units": forecast["hourly_units"],
                    "latitude" : decimal.Decimal(str(forecast["latitude"])),
                    "longitude" : decimal.Decimal(str(forecast["longitude"])),
                    "timezone" : forecast["timezone"],
                    "timezone_abbreviation" : forecast["timezone_abbreviation"],
                    "utc_offset_seconds" : decimal.Decimal(str(forecast["utc_offset_seconds"])),
                }
            }
            weather_table.put_item(Item=item)
        except Exception as e:
            _LOG.error(f"Failed to save forecast to DynamoDB: {e}")
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed to save forecast to DynamoDB"})
            }

        return {
            "statusCode": 200,
            "body": json.dumps(forecast)
        }
    

HANDLER = Processor()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)
