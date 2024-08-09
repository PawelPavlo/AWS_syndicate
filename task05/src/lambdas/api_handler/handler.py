import datetime
import json
import os
import uuid

import boto3

from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger('ApiHandler-handler')


class ApiHandler(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass

    def handle_request(self, event, context):
        """
        Explain incoming event here
        """
        _LOG.info(f'Event: {event}')

        # Create a DynamoDB resource object
        dynamodb = boto3.resource('dynamodb')

        # Get the DynamoDB table
        # table = dynamodb.Table('Events')
        table_name = os.environ.get('target_table')
        _LOG.info(f'target_table: {table_name}')
        table = dynamodb.Table(table_name)

        now = datetime.datetime.now()
        iso_format = now.isoformat()

        try:
            item = {
                "id": str(uuid.uuid4()),
                "principalId": event['principalId'],
                "createdAt": iso_format,
                "body": event['content']
            }
        except Exception as error:
            _LOG.warning(error)
            body = event['body']
            data = json.loads(body)
            _LOG.info(f'body: {body}')
            _LOG.info(f'data: {data}')

            item = {
                "id": str(uuid.uuid4()),
                "principalId": data['principalId'],
                "createdAt": iso_format,
                "body": data
            }
            event = data

        response = table.put_item(Item=item)
        _LOG.info(f'DynamoDB put_item response: {response}')
        return {
            "statusCode": 201,
            "event": event,
        }


HANDLER = ApiHandler()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)