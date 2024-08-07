from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda
import json
_LOG = get_logger('HelloWorld-handler')


class HelloWorld(AbstractLambda):

    def validate_request(self, event) -> dict:
        # Check if the request path is /hello
        if event.get('path') == '/hello':
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Hello from Lambda"})
            }
        else:
            # Return None to indicate that the request is not for this endpoint
            return None

    def handle_request(self, event, context):
        """
        Explain incoming event here
        """
        # todo implement business logic
        # if event.get('path') == '/hello':
        return {
            'statusCode': 200,
            'message': 'Hello from Lambda'
        }


HANDLER = HelloWorld()


def lambda_handler(event, context):
    # Validate the request
    response = HANDLER.validate_request(event)
    if response:
        return response

    # If the request is not for /hello, handle it using the handle_request method
    return HANDLER.lambda_handler(event=event, context=context)
