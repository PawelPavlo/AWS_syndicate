from tests.test_api_handler import ApiHandlerLambdaTestCase
from unittest.mock import patch
import json

class TestSuccess(ApiHandlerLambdaTestCase):

    @patch("boto3.resource")
    def test_success(self, mock_resource):
        self.event = {
            "body": json.dumps({
                "principalId": 1,
                "content": {"name": "John", "surname": "Doe"}
            })
        }
        self.context = {}
        print(self.event)
        mock_table = mock_resource.return_value.Table.return_value
        mock_table.put_item.return_value = {}

        response = self.HANDLER.handle_request(self.event, self.context)

        self.assertEqual(response["statusCode"], 201)
        
