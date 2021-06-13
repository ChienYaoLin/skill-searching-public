import json
import boto3

from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return json.JSONEncoder.default(self, obj)

def lambda_handler(event, context):
    # TODO implement
    
    job_id = event['queryStringParameters']['query']
    comprehend = boto3.client('comprehend', 
                        region_name='ap-southeast-2',
                        aws_access_key_id='access_key_id',
                        aws_secret_access_key='secret_access_key')
                        
    res = comprehend.describe_entities_detection_job(JobId=job_id)
    status = res['EntitiesDetectionJobProperties']
    
    return {
        'statusCode': 200,
        'body': json.dumps(res, cls=DateTimeEncoder)
    }
