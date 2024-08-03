from tests.test_hello_world import HelloWorldLambdaTestCase
import json

class TestHelloWorldLambda(HelloWorldLambdaTestCase):

    def test_success_get_hello(self):
        # Test a valid request
        test_event = {
            'rawPath': '/hello',
            'requestContext': {
                'http': {
                    'method': 'GET'
                }
            }
        }
        test_context = {}

        expected_response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'statusCode': 200,
                'message': 'Hello from Lambda'
            })
        }

        actual_response = self.HANDLER.handle_request(test_event, test_context)
        self.assertEqual(actual_response, expected_response)

    def test_failure_unsupported_path(self):
        # Test an unsupported path
        test_event = {
            'rawPath': '/unknown',
            'requestContext': {
                'http': {
                    'method': 'GET'
                }
            }
        }
        test_context = {}

        expected_response = {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'statusCode': 400,
                'message': 'Bad request syntax or unsupported method. Request path: /unknown. HTTP method: GET'
            })
        }

        actual_response = self.HANDLER.handle_request(test_event, test_context)
        self.assertEqual(actual_response, expected_response)

    def test_failure_unsupported_method(self):
        # Test an unsupported HTTP method
        test_event = {
            'rawPath': '/hello',
            'requestContext': {
                'http': {
                    'method': 'POST'
                }
            }
        }
        test_context = {}

        expected_response = {
            'statusCode': 400,
            'headers': {
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'statusCode': 400,
                'message': 'Bad request syntax or unsupported method. Request path: /hello. HTTP method: POST'
            })
        }

        actual_response = self.HANDLER.handle_request(test_event, test_context)
        self.assertEqual(actual_response, expected_response)

