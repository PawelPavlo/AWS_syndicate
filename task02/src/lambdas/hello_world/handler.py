import json
from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda

_LOG = get_logger('HelloWorld-handler')

class HelloWorld(AbstractLambda):
    def validate_request(self, event) -> dict:
        # Extend this method to validate params before handling requests if needed
        pass

    def handle_request(self, event, context):
        """
        Processes incoming HTTP requests sent through Lambda's Function URL.
        Checks request path and method to ensure it's handling the correct endpoint.
        """
        path = event.get('rawPath')
        method = event.get('requestContext', {}).get('http', {}).get('method')
        _LOG.info(f'Received request with path: {path} and method: {method}')

        # Preparing headers for all HTTP responses
        headers = {
            'Content-Type': 'application/json'
        }

        # Check if the incoming request is targeting /hello via GET method
        if path == '/hello' and method == 'GET':
            response_body = {
                'statusCode': 200,
                'message': 'Hello from Lambda'
            }
            _LOG.info('Returning successful response for /hello GET')
            response = {
                'statusCode': 200,
                'headers': headers,
                'body': json.dumps(response_body)
            }
            return response
        else:
            # Correct error messaging to match the expected output
            error_message = f'Bad request syntax or unsupported method. Request path: {path}. HTTP method: {method}'
            _LOG.error(error_message)
            response_body = {
                'statusCode': 400,
                'message': error_message
            }
            return {
                'statusCode': 400,
                'headers': headers,
                'body': json.dumps(response_body)
            }

HANDLER = HelloWorld()

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Log start and completion of the handler execution.
    """
    _LOG.info('Handler execution started')
    response = HANDLER.handle_request(event, context)
    _LOG.info('Handler execution completed')
    return response
