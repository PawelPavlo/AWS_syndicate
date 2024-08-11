from commons.log_helper import get_logger
from commons.abstract_lambda import AbstractLambda
import json
import boto3
import datetime
import uuid
import os
 
_LOG = get_logger('UuidGenerator-handler')
 
class UuidGenerator(AbstractLambda):
 
    def validate_request(self, event) -> dict:
        pass
    def handle_request(self, event, context):
        # Generate 10 random UUIDs
        uuids = [str(uuid.uuid4()) for _ in range(10)]
 
        current_time = datetime.datetime.utcnow()
 
        # Format the current time in ISO 8601 format
        iso_time = current_time.isoformat(timespec='milliseconds') + "Z"
 
        # Get the current execution time and format it for the filename
        filename = f"{iso_time}"
        # Join the UUIDs into a single string, each on a new line
        content = "\n".join(uuids)
        s3content = {
            "ids": uuids
        }
        json_s3content = json.dumps(s3content)
        print(json_s3content)
        # Specify your S3 bucket name
        # bucket_name = 'cmtr-db42d8b8-uuid-storage'  # Change this to your bucket name
        # function_name = os.environ['AWS_LAMBDA_FUNCTION_NAME']
        lambda_function_name = context.function_name
        bucket_name = lambda_function_name.replace("uuid_generator", "uuid-storage")
        print("function_name:", lambda_function_name)
        print("Bucket name:", bucket_name)
        # Initialize S3 client
        s3 = boto3.client('s3')
        # Upload the UUIDs to S3
        s3.put_object(Bucket=bucket_name, Key=filename, Body=json_s3content)
        return {
            'statusCode': 200,
            'body': json.dumps(f"UUIDs generated and saved to {bucket_name}/{filename}")
        }

 
HANDLER = UuidGenerator()
 
 
def lambda_handler(event, context):
    return HANDLER.lambda_handler(event=event, context=context)