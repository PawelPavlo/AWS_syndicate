import json
import os
import re
import traceback
import uuid
from datetime import datetime
from decimal import Decimal

import boto3
from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger('ApiHandler-handler')


def is_time_in_slot(start: str, end: str, tested_time):
    # Convert strings to time objects
    start = datetime.strptime(start, "%H:%M").time()
    end = datetime.strptime(end, "%H:%M").time()
    time = datetime.strptime(tested_time, "%H:%M").time()

    # Check if the given time is within the slot
    return start <= time <= end


def convert_decimals_to_int(i):
    if isinstance(i, list):
        return [convert_decimals_to_int(i) for i in i]
    elif isinstance(i, dict):
        return {k: convert_decimals_to_int(v) for k, v in i.items()}
    elif isinstance(i, Decimal):
        return int(i)
    else:
        return i


def validate_email(email):
    # Regular expression for email validation
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(pattern, email):
        _LOG.info('Bad email')
        raise Exception('Bad email')


def validate_password(password):
    # Regular expression for password validation
    pattern = r'^(?=.*[a-zA-Z])(?=.*[0-9])(?=.*[^\w\s]).{12,}$'
    if not re.match(pattern, password):
        _LOG.info('Bad password')
        raise Exception('Bad password')


def write_to_dynamo(table_name: str, item: dict):
    dynamodb = boto3.resource('dynamodb')

    _LOG.info(f'TARGET_TABLE: {table_name}')
    table = dynamodb.Table(table_name)
    # item = json.loads(json.dumps(item), parse_float=Decimal)
    dynamo_response = table.put_item(Item=item)
    _LOG.info(dynamo_response)


def sign_up(sing_up_request: dict):
    _LOG.info('Sign up request')
    client = boto3.client('cognito-idp')

    user_pool_name = os.environ['USER_POOL']
    _LOG.info(f'user_pool_name: {user_pool_name}')

    response = client.list_user_pools(MaxResults=60)

    user_pool_id = None
    for user_pool in response['UserPools']:
        if user_pool['Name'] == user_pool_name:
            user_pool_id = user_pool['Id']
            _LOG.info(f'user_pool_id: {user_pool_id}')
            break

    username = sing_up_request['email']
    password = sing_up_request['password']
    given_name = sing_up_request['firstName']
    family_name = sing_up_request['lastName']

    validate_email(username)
    validate_password(password)

    # Create the user
    response = client.admin_create_user(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[
            {
                'Name': 'email',
                'Value': username
            },
            {
                'Name': 'given_name',
                'Value': given_name
            },
            {
                'Name': 'family_name',
                'Value': family_name
            },
        ],
        TemporaryPassword=password,
        MessageAction='SUPPRESS'
    )

    _LOG.info(f'Cognito sign up response: {response}')

    # Set a new permanent password for the user
    resp = client.admin_set_user_password(
        UserPoolId=user_pool_id,
        Username=username,
        Password=password,
        Permanent=True
    )

    _LOG.info(f'set_user_password permanent response: {resp}')


def sign_in(sing_in_request):
    _LOG.info('Sign in request')

    username = sing_in_request['email']
    password = sing_in_request['password']

    validate_email(username)
    validate_password(password)

    client = boto3.client('cognito-idp')

    user_pool_name = os.environ['USER_POOL']
    _LOG.info(f'user_pool_name: {user_pool_name}')

    response = client.list_user_pools(MaxResults=60)

    user_pool_id = None
    for user_pool in response['UserPools']:
        if user_pool['Name'] == user_pool_name:
            user_pool_id = user_pool['Id']
            _LOG.info(f'user_pool_id: {user_pool_id}')
            break

    response = client.list_user_pool_clients(
        UserPoolId=user_pool_id,
        MaxResults=10
    )

    client_app = 'my_client_app'
    for app_client in response['UserPoolClients']:
        if app_client['ClientName'] == client_app:
            app_client_id = app_client['ClientId']

    response = client.initiate_auth(
        ClientId=app_client_id,
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': username,
            'PASSWORD': password
        }
    )

    access_token = response['AuthenticationResult']['AccessToken']
    id_token = response['AuthenticationResult']['IdToken']

    _LOG.info(f'Cognito sign in response: {response}')

    return {
        'statusCode': 200,
        # 'body': json.dumps({'accessToken': access_token})
        'body': json.dumps({'accessToken': id_token})
     }


def tables_post(item: dict):
    _LOG.info('/tables POST')
    _LOG.info(f'item: {item}')
    try:
        table_name = os.environ['TABLES_TABLE']
        _LOG.info(f'TABLES_TABLE: {table_name}')
        write_to_dynamo(table_name, item)
    except Exception as error:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': error})
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({'id': item['id']})
        }


def tables_get() -> dict:
    _LOG.info('/tables GET')
    try:
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ['TABLES_TABLE']
        _LOG.info(f'TABLES_TABLE: {table_name}')

        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response['Items']
        items = convert_decimals_to_int(items)
        items = sorted(items, key=lambda item: item['id'])

        result = {'tables': items}
        _LOG.info(f'Tables fetched: {result}')
    except Exception as error:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': error})
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }


def tables_get_by_id(table_id: int) -> dict:
    try:
        _LOG.info('/tables/{tableId} GET')
        dynamodb = boto3.resource('dynamodb')
        table_name = os.environ['TABLES_TABLE']
        _LOG.info(f'TABLES_TABLE: {table_name}')

        table = dynamodb.Table(table_name)
        item = table.get_item(Key={'id': int(table_id)})
        item = item['Item']
        item = convert_decimals_to_int(item)
        _LOG.info(item)
    except Exception as error:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': error})
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps(item)
        }


def reservations_post(item: dict):
    _LOG.info('/reservations POST')
    _LOG.info(f'item: {item}')

    # Check if a table exists
    table_name = os.environ['TABLES_TABLE']
    _LOG.info(f'TABLES_TABLE (reserv post): {table_name}')
    dynamodb = boto3.resource('dynamodb')

    table = dynamodb.Table(table_name)
    response = table.scan()
    _LOG.info(f'Scan response: {response}')
    items = response['Items']
    items = convert_decimals_to_int(items)

    required_table_number = item['tableNumber']
    for table in items:
        _LOG.info(f'table item: {table}')
        if table['number'] == required_table_number:
            _LOG.info(f'Table found: {required_table_number}')
            break
    else:
        _LOG.info(f'No such table')
        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': 'Table does not exist'})
        }

    # Handle conflicting reservations
    reservations = _get_reservations()
    # {'reservations': [{'phoneNumber': '0661902100', 'clientName': 'John Doe', 'date': '2024-05-19', 'slotTimeStart': '13:00', 'slotTimeEnd': '15:00', 'id': '6cfd60a3-b575-4a62-8596-00be6bc61f08', 'tableNumber': 25}]}
    for i in reservations['reservations']:
        if i['date'] == item['date'] and i['tableNumber'] == item['tableNumber']:
            if is_time_in_slot(i['slotTimeStart'], i['slotTimeEnd'], item['slotTimeStart']) or is_time_in_slot(i['slotTimeStart'], i['slotTimeEnd'], item['slotTimeEnd']):
                return {
                    'statusCode': 400,
                    'body': json.dumps({'Error message': f'Overlapping time'})
                }

    try:
        table_name = os.environ['RESERVATION_TABLE']
        _LOG.info(f'RESERVATION_TABLE try: {table_name}')
        reservation_id = str(uuid.uuid4())
        item.update({'id': reservation_id})
        _LOG.info(f'updated item: {item}')
        write_to_dynamo(table_name, item)
    except Exception as error:
        traceback_str = traceback.format_exc()
        print(traceback_str)

        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': error})
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({'reservationId': reservation_id})
        }


def _get_reservations() -> dict:
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ['RESERVATION_TABLE']
    _LOG.info(f'RESERVATION_TABLE: {table_name}')

    table = dynamodb.Table(table_name)
    response = table.scan()
    items = response['Items']
    items = convert_decimals_to_int(items)

    result = {'reservations': items}
    _LOG.info(f'Reservations fetched: {result}')
    return result


def reservations_get() -> dict:
    _LOG.info('/reservations GET')
    try:
        result = _get_reservations()

    except Exception as error:
        return {
            'statusCode': 400,
            'body': json.dumps({'Error message': error})
        }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }


class ApiHandler(AbstractLambda):
        
    def handle_request(self, event, context):
        _LOG.info(f'Event: {event}')

        try:
            if event['path'] == '/signup' and event['httpMethod'] == 'POST':
                body = json.loads(event['body'])
                sign_up(body)
                return {
                    'statusCode': 200,
                    'body': json.dumps({'status': 200, 'message': 'Signup successful'})
                }
            elif event['path'] == '/signin' and event['httpMethod'] == 'POST':
                body = json.loads(event['body'])
                lambda_response_with_token = sign_in(body)
                _LOG.info(f'lambda_response: {lambda_response_with_token}')
                return lambda_response_with_token
            elif event['path'] == '/tables' and event['httpMethod'] == 'POST':
                body = json.loads(event['body'])
                return tables_post(body)
            elif event['path'] == '/tables' and event['httpMethod'] == 'GET':
                return tables_get()
            elif event['resource'] == '/tables/{tableId}' and event['httpMethod'] == 'GET':
                table_id = int(event['path'].split('/')[-1])
                return tables_get_by_id(table_id)
            elif event['path'] == '/reservations' and event['httpMethod'] == 'POST':
                body = json.loads(event['body'])
                return reservations_post(body)
            elif event['path'] == '/reservations' and event['httpMethod'] == 'GET':
                return reservations_get()
            else:
                _LOG.info('Unsupported request type for my task10 app')
                return {
                    'statusCode': 400,
                    'body': json.dumps({'Error message': 'Unsupported request type for my task10 app'})
                }
        except Exception as error:
            _LOG.info('Invalid request')
            _LOG.info(f'Error: {error}')

            lambda_error_response = {
                'statusCode': 400,
                'body': json.dumps({
                    'statusCode': 400,
                    'error': 'Bad request',
                    'message': f'{error}'
                })
            }
            traceback_str = traceback.format_exc()
            print(traceback_str)

            _LOG.info(f'lambda_error_response: {lambda_error_response}')
            return lambda_error_response


HANDLER = ApiHandler()


def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)
