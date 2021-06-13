import boto3
import json
import requests
import unicodedata
import uuid
from bs4 import BeautifulSoup
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return json.JSONEncoder.default(self, obj)


region = 'ap-southeast-2'
service = 'es'
s3_local = boto3.resource('s3')
s3_comprehend = boto3.resource('s3', 
                region_name='ap-southeast-2',
                aws_access_key_id='access_key_id',
                aws_secret_access_key='secret_access_key')
entityRecognizerArn = "arn:aws:comprehend:ap-southeast-2:252850029174:entity-recognizer/SkillRecognizer"
dataAccessRoleArn = 'arn:aws:iam::252850029174:role/comprehend-role-demo'
jobBucket = 'assignment3-skill-searching'
compBucket = 'skill-comprehend-result'

# return job urls from seek with certain keyword, default data of first 5 pages 
def getUrlSeek(keyWord, page = 1):
    keyString = keyWord.replace(' ', '-')
    mainUrl = 'https://www.seek.com.au'
    jobUrlList = []
    for i in range(1, 1+page):
        url = mainUrl + '/' + keyString + '-jobs?page=' + str(i)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        jobsSoup = soup.select("article")
        for jobSoup in jobsSoup:
            jobUrlList.append('https://www.seek.com.au/job/'+jobSoup.attrs['data-job-id'])
    return jobUrlList

# Lambda execution starts here
def lambda_handler(event, context):
    
    keyword = event['queryStringParameters']['query']
    userId = event['headers']['userId']
    urlList = getUrlSeek(keyword)
   
    comprehend = boto3.client('comprehend', 
                        region_name='ap-southeast-2',
                        aws_access_key_id='access_key_id',
                        aws_secret_access_key='secret_access_key')

    job_id = str(uuid.uuid4())
    # crawl job desc
    whole_text = ''
    for url in urlList:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.find('title').contents[0]
        all_text_tag = soup.select('.WaMPc_4')
        for text_tag in all_text_tag:
            line = text_tag.text
            whole_text = whole_text + line + '\n'
            
    file_name='job_desc/'+str(job_id)+".txt"
    # file_name='job_desc/test.txt'
    
    obj=s3_comprehend.Object(jobBucket, file_name)
    obj.put(Body = whole_text)
    
    # submit aws comprehend task to find the entities
    entity_res = comprehend.start_entities_detection_job(
        EntityRecognizerArn=entityRecognizerArn,
        JobName=str(job_id),
        LanguageCode="en",
        DataAccessRoleArn=dataAccessRoleArn,
        InputDataConfig={
            "InputFormat": "ONE_DOC_PER_LINE",
            "S3Uri": "s3://" + jobBucket + "/"+file_name
        },
        OutputDataConfig={
            "S3Uri": "s3://" + compBucket + "/result/"+ keyword + "/" + userId + "/"
        }
    )
    
    res = comprehend.describe_entities_detection_job(JobId=entity_res['JobId'])
    
    response = {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": '*'
        },
        "isBase64Encoded": False
    }
    response['body'] = json.dumps(res, cls=DateTimeEncoder)
    
    return response





