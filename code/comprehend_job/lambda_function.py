import json
import urllib.parse
import boto3
import tarfile
import uuid
import io
from datetime import datetime

s3_local = boto3.resource('s3')
dynamodb = boto3.resource('dynamodb', region_name = 'ap-southeast-2')
s3_comprehend = boto3.resource('s3', 
                aws_access_key_id='access_key_id',
                aws_secret_access_key='secret_access_key')



def lambda_handler(event, context):

    # Get the object from the event and show its content type
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    key_split = key.split('/')
    
    keyword = key_split[1]
    userId = key_split[2]
    jobId = key_split[3].split('-')[2]
    
    obj = s3_comprehend.Object(bucket, key)
    wholefile = obj.get()["Body"].read()
    fileobj = io.BytesIO(wholefile)
    tarf = tarfile.open(fileobj=fileobj)
    tarf_str = tarf.extractfile('output').read()
    json_str_list = tarf_str.decode('utf8').split('\n')

    
    # UPDATE Task
    table = dynamodb.Table('UserOwnTask')
    response = table.update_item(
        Key={
            'user_id': userId,
            'task_id': jobId
        },
        UpdateExpression="set end_time=:et, task_status=:sta, last_update=:lu",
        ExpressionAttributeValues={
            ':et': str(datetime.now().replace(microsecond=0)),
            ':sta': 'COMPLETED',
            ':lu': str(datetime.now().replace(microsecond=0))
        },
        ReturnValues="UPDATED_NEW"
    )
    

    
    # PUT skills
    table = dynamodb.Table('search_result')
    id=1
    with table.batch_writer() as batch:
        for json_str in json_str_list:
            if 'Entities' in json_str:
                dict_ent = json.loads(json_str)
                for entity in dict_ent['Entities']:
                    batch.put_item(
                        Item={
                            'key_word': keyword.lower(),
                            'skill_id': jobId+'-'+f'{id:05}',
                            'skill': entity['Text'],
                            'date': (datetime.now()).isoformat()
                        }
                    )
                    id+=1
    
    
