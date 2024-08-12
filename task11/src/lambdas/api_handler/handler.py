import json
import os
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import boto3
from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

dynamodb = boto3.resource('dynamodb', region_name='eu-central-1')
boto_client = boto3.client('cognito-idp')
reservations_table_name = 'cmtr-b5eedb66-Reservations-test'
tables_table_name = 'cmtr-b5eedb66-Tables-test'
user_pool_name = 'cmtr-b5eedb66-simple-booking-userpool-test'
CLIENT_APP = 'client_app'

_LOG = get_logger('ApiHandler-handler')


def decimal_serializer(obj):
    if isinstance(obj, Decimal):
        return int(obj)
    raise TypeError("Type not serializable")


def check_table_existence(tables_table, table_number):
    response = tables_table.scan()
    tables = response['Items']
    for table in tables:
        if table["number"] == table_number:
            return
    raise KeyError("Not existing table")


class ApiHandler(AbstractLambda):

    def validate_request(self, event) -> dict:
        pass

    def handle_request(self, event, context):
        """
        Explain incoming event here
        """
        _LOG.info(f"{event=}")

        tables_table = dynamodb.Table(tables_table_name)
        reservations_table = dynamodb.Table(reservations_table_name)

        try:
            if event['path'] == '/signup' and event['httpMethod'] == 'POST':
                _LOG.info("signup post")
                body = json.loads(event['body'])
                first_name = body['firstName']
                last_name = body['lastName']
                email = body['email']
                password = body['password']

                response = boto_client.list_user_pools(MaxResults=60)
                user_pool_id = None
                for user_pool in response['UserPools']:
                    if user_pool['Name'] == user_pool_name:
                        user_pool_id = user_pool['Id']
                        break
                _LOG.info(f'{user_pool_id=}')

                app_client_id = None
                response = boto_client.list_user_pool_clients(UserPoolId=user_pool_id)
                _LOG.info(f"{response=}")

                for app_client in response['UserPoolClients']:
                    if app_client['ClientName'] == CLIENT_APP:
                        app_client_id = app_client['ClientId']
                _LOG.info(f'{app_client_id =}')

                response = boto_client.admin_create_user(
                    UserPoolId=user_pool_id,
                    Username=email,
                    UserAttributes=[
                        {
                            'Name': 'email',
                            'Value': email
                        },
                        {
                            'Name': 'given_name',
                            'Value': first_name
                        },
                        {
                            'Name': 'family_name',
                            'Value': last_name
                        },
                    ],
                    TemporaryPassword=password,
                    MessageAction='SUPPRESS'
                )
                _LOG.info(f'{response=}')

                response = boto_client.admin_set_user_password(
                    UserPoolId=user_pool_id,
                    Username=email,
                    Password=password,
                    Permanent=True
                )
                _LOG.info(f'{response=}')

            elif event['path'] == '/signin' and event['httpMethod'] == 'POST':
                body = json.loads(event['body'])
                _LOG.info("signip post")

                email = body['email']
                password = body['password']

                response = boto_client.list_user_pools(MaxResults=60)
                _LOG.info(f'{response=}')
                user_pool_id = None
                for user_pool in response['UserPools']:
                    if user_pool['Name'] == user_pool_name:
                        user_pool_id = user_pool['Id']
                        break
                _LOG.info(f'{user_pool_id=}')

                response = boto_client.list_user_pool_clients(
                    UserPoolId=user_pool_id,
                    MaxResults=10
                )

                app_client_id = None
                for app_client in response['UserPoolClients']:
                    if app_client['ClientName'] == CLIENT_APP:
                        app_client_id = app_client['ClientId']

                response = boto_client.initiate_auth(
                    ClientId=app_client_id,
                    AuthFlow='USER_PASSWORD_AUTH',
                    AuthParameters={
                        'USERNAME': email,
                        'PASSWORD': password
                    }
                )
                _LOG.info(f'{response=}')
                id_token = response['AuthenticationResult']['IdToken']
                return {
                    'statusCode': 200,
                    'body': json.dumps({'accessToken': id_token})
                }

            elif event['path'] == '/tables' and event['httpMethod'] == 'POST':
                _LOG.info("tables post")

                item = json.loads(event['body'])
                response = tables_table.put_item(Item=item)
                _LOG.info(response)
                return {"statusCode": 200,
                        "body": json.dumps({"id": item["id"]})
                        }

            elif event['path'] == '/tables' and event['httpMethod'] == 'GET':
                response = tables_table.scan()
                items = response['Items']
                _LOG.info(items)

                items = sorted(items, key=lambda item: item['id'])
                tables = {'tables': sorted(items, key=lambda item: item['id'])}

                body = json.dumps(tables, default=decimal_serializer)

                return {"statusCode": 200, "body": body}

            elif event['resource'] == '/tables/{tableId}' and event['httpMethod'] == 'GET':
                table_id = int(event['path'].split('/')[-1])

                item = tables_table.get_item(Key={'id': int(table_id)})
                body = json.dumps(item["Item"], default=decimal_serializer)
                _LOG.info(f"{body=}")
                return {"statusCode": 200, "body": body}

            elif event['path'] == '/reservations' and event['httpMethod'] == 'POST':
                _LOG.info("reservations post")
                item = json.loads(event['body'])
                proposed_table_number = item["tableNumber"]
                try:
                    check_table_existence(tables_table, proposed_table_number)
                except KeyError:
                    return {"statusCode": 400, "body": json.dumps({"error": "table does not exist"})}
                _LOG.info(f"{proposed_table_number=}")

                proposed_slot_time_start = datetime.strptime(item["slotTimeStart"], "%H:%M").time()
                proposed_slot_time_end = datetime.strptime(item["slotTimeEnd"], "%H:%M").time()
                response = reservations_table.scan()

                reservations = response['Items']
                for r in reservations:
                    if r["tableNumber"] != proposed_table_number:
                        continue
                    if r["date"] != item["date"]:
                        continue
                    existing_slot_time_start = datetime.strptime(r["slotTimeStart"], "%H:%M").time()
                    existing_slot_time_end = datetime.strptime(r["slotTimeEnd"], "%H:%M").time()
                    if any([existing_slot_time_start <= proposed_slot_time <= existing_slot_time_end
                            for proposed_slot_time in (proposed_slot_time_start, proposed_slot_time_end)]):
                        return {"statusCode": 400,
                                "body": json.dumps({"error": "time slots are overlapping with existing reservations"})}
                reservation_id = str(uuid4())
                response = reservations_table.put_item(Item={"id": reservation_id, **item})
                _LOG.info(response)
                return {"statusCode": 200,
                        "body": json.dumps({"reservationId": reservation_id})
                        }

            elif event['path'] == '/reservations' and event['httpMethod'] == 'GET':
                _LOG.info("reservations get")

                response = reservations_table.scan()
                items = response['Items']

                for i in items:
                    del i["id"]

                items = sorted(items, key=lambda item: item['tableNumber'])
                _LOG.info(items)
                reservations = {"reservations": items}
                _LOG.info(reservations)
                return {"statusCode": 200, "body": json.dumps(reservations, default=decimal_serializer),
                        "headers":    {'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                                       'Access-Control-Allow-Origin': '*',
                                       'Access-Control-Allow-Methods': '*',
                                       'Accept-Version': '*'}
                        }

            else:
                raise KeyError("no method")

        except Exception as e:
            _LOG.info('Bad request')
            _LOG.info(f'Error: {e}')

            message = {
                'statusCode': 400,
                'body': json.dumps({
                    'statusCode': 400,
                    'error': 'Bad request',
                    'message': f'{e}'
                })
            }

            _LOG.info(f'{message=}')
            return message
        return {"statusCode": 200, "body": json.dumps(event)}


HANDLER = ApiHandler()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)