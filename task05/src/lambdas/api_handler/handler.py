from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda
import boto3
import uuid
import json
from datetime import datetime


_LOG = get_logger('ApiHandler-handler')


class ApiHandler(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass

    def handle_request(self, event, context):
        """
        Explain incoming event here
        """
        # todo implement business logic
        _LOG.info(event)
        db = boto3.resource("dynamodb")
        table_name = "cmtr-b5eedb66-Events-test"
        _LOG.info(f"table name: {table_name}")
        table = db.Table(table_name)

        now = datetime.now().isoformat()
        _LOG.info("Inserting...")
        obj = {
            "id": str(uuid.uuid4()),
            "principalId": event["principalId"],
            "createdAt": now,
            "body": event
        }
        table.put_item(Item=obj)
        return {
            "statusCode": 201,
            "event": obj,
        }

HANDLER = ApiHandler()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)