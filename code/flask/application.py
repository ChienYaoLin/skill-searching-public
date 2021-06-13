import os
from flask import Flask, render_template, request, redirect, session, flash
import boto3, io
import requests, json
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, time
from pprint import pprint
from wordcloud import WordCloud
import matplotlib.pyplot as plt

#initialise flask app 
application = Flask(__name__)
app = application
application.secret_key = "something"


create_job_endpoint = "https://n9yc1vkshj.execute-api.ap-southeast-2.amazonaws.com/skillsearching/create-job"
check_job_endpoint = "https://n9yc1vkshj.execute-api.ap-southeast-2.amazonaws.com/skillsearching/check-job"
x_api_key = 'key'
jobBucket = 'assignment3-skill-searching'

dynamodb = boto3.resource('dynamodb', region_name = 'ap-southeast-2')
table = dynamodb.Table('Users')

@application.route('/') 
def root():  
    return render_template('home.html')

@application.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_id'):
        return redirect("/main")
    if request.method == 'GET':
        return render_template('login.html', error = "")
    elif request.method == 'POST':
        user_id = request.form["userid"]
        password = request.form["password"]
        user_details = user_exist(user_id)
        if not(user_details) or (user_details[0]["password"] != password):
            error_message = "Ooppss !! Invalid ID or password. Please check your Credentials"
            return render_template('login.html', error = error_message)
        session["user_id"] = user_details[0]["user_id"]
        session["name"] = user_details[0]["name"]
        session["password"] = user_details[0]["password"]
        #print (session["name"])
        return redirect("/main")

@application.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template('register.html', error = "")
    elif request.method == 'POST':
        user_id = request.form["userid"]
        username = request.form["user_name"]
        password = request.form["password"]
        
        if(user_exist(user_id)):
            error_message = "Ooppss !! The ID already exists"
            return render_template('register.html', error = error_message)
        else:
            add_user(user_id, password, username)
            print(user_id)
            return redirect('login')

def user_exist(user_id):
    table = dynamodb.Table("Users")
    response = table.query(
         KeyConditionExpression=Key('user_id').eq(user_id)
    )
    return response['Items']

def add_user(user_id, password, username):
    table = dynamodb.Table("Users")
    response = table.put_item(
       Item={
            'user_id' : user_id,
            'name': username,
            'password': password,
        }
    )
    return response  

@application.route('/search', methods=['GET', 'POST']) 
def search():
    if request.method == 'POST':
        if ifInProgessTask():
            flash('Another your job is still in progress. Please wait!')
        else:
            # submit task to aws comprehend
            query = request.form['inputString']
            params = {'query': query}
            headers = {'x-api-key': x_api_key, 'userId': session['user_id']}
            currentTask = requests.request('GET', create_job_endpoint, params=params ,headers=headers)
            response = json.loads(currentTask.text)
            task_id = response['EntitiesDetectionJobProperties']['JobId']
            start_time = response['EntitiesDetectionJobProperties']['SubmitTime']
            status = response['EntitiesDetectionJobProperties']['JobStatus']
            flash("Detection Job has been submitted to AWS Comprehend. Please wait around 7 minutes.")
            # put task status to DB
            table = dynamodb.Table("UserOwnTask")
            res = table.put_item(
                Item={
                    'searchQuery': query,
                    'user_id': session["user_id"],
                    'task_id' : task_id,
                    'start_time' : start_time,
                    'end_time' : '',
                    'task_status' : status,
                    'last_update' : str(datetime.now().replace(microsecond=0))
                }
            )
    else:
        flash('Invalid action! Please search from the main page.')

    return render_template('search.html')

@application.route('/searchresult' , methods=['GET', 'POST']) 
def searchresult():
    search_query = query_search()
    updateTaskStatus()
    return render_template('searchresult.html', usertasks = search_query)

def ifInProgessTask():
    userTasks = query_search()
    for task in userTasks:
        if (task["task_status"] == 'IN_PROGRESS') or (task["task_status"] == 'SUBMITTED'):
            return True
    return False

def updateTaskStatus():
    userTasks = query_search()
    for task in userTasks:
        if task['task_status'] != 'COMPLETED':
            last_update = datetime.strptime(task['last_update'], '%Y-%m-%d %H:%M:%S')
            diff_in_s = (datetime.now()-last_update).total_seconds()
            if diff_in_s > 60:
                params = {'query': task['task_id']}
                headers = {'x-api-key': x_api_key}
                checkTask = requests.request('GET', check_job_endpoint, params=params ,headers=headers)
                response = json.loads(checkTask.text)
                status = response['EntitiesDetectionJobProperties']['JobStatus']
                table = dynamodb.Table('UserOwnTask')
                if status == 'COMPLETED':
                    response = table.update_item(
                        Key={
                            'user_id': session['user_id'],
                            'task_id': task['task_id']
                        },
                        UpdateExpression="set end_time=:et, task_status=:sta, last_update=:lu",
                        ExpressionAttributeValues={
                            ':et': response['EntitiesDetectionJobProperties']['EndTime'],
                            ':sta': status,
                            ':lu': str(datetime.now().replace(microsecond=0))
                        },
                        ReturnValues="UPDATED_NEW"
                    )
                else:
                    response = table.update_item(
                        Key={
                            'user_id': session['user_id'],
                            'task_id': task['task_id']
                        },
                        UpdateExpression="set task_status=:sta, last_update=:lu",
                        ExpressionAttributeValues={
                            ':sta': status,
                            ':lu': str(datetime.now().replace(microsecond=0))
                        },
                        ReturnValues="UPDATED_NEW"
                    )



def query_search():
    table = dynamodb.Table("UserOwnTask")
    response = table.scan(
    FilterExpression = Attr('user_id').eq(session["user_id"])
    )
    return response['Items']    
      

@application.route('/tasks' ,methods=['GET', 'POST']) 
def tasks():  
    task_id = request.args.get('id')
    key_word = request.args.get('key')
    table = dynamodb.Table("search_result")
    response = table.query(
        ProjectionExpression="skill, skill_id",
        KeyConditionExpression=Key('key_word').eq(key_word.lower())
    )
    skills = response['Items']
    words = []
    for skill in skills:
        words.append(skill['skill'])
    if len(words) == 0:
        task_id='notReady'
    else:
        wordcloud = WordCloud(
            width=1000,
            height=600,
            background_color='white',
            max_words=200,
            max_font_size=80,
            scale=3,
            random_state=42
        ).generate(' '.join(words))
        plt.figure( figsize=(10,6), facecolor='k')
        plt.imshow(wordcloud)
        plt.axis("off")
        plt.tight_layout(pad=0)
        img_data = io.BytesIO()
        plt.savefig(img_data, format='png')
        img_data.seek(0)

        s3 = boto3.resource('s3') 
        bucket = s3.Bucket(jobBucket)
        bucket.put_object(Body=img_data, ContentType='image/png', Key="entities/"+task_id+'.png', ACL='public-read')
    

    # flash(str(words))


    return render_template('tasks.html', task_id=task_id)    



@application.route('/changename',methods=['GET', 'POST']) 
def changename():  
    if request.method == 'GET':
        return render_template('changename.html', error = "")
    else:
        request.method == 'POST'
        newname = request.form["changename"]
        currentName = session["user_id"]
        upd_name(newname, currentName)
        return render_template('main.html' ,username=session["name"])
        

def upd_name(newname, currentName):
    #print (newname +" "+currentName)
    table = dynamodb.Table("Users")
    response = table.update_item(
    Key={
        'user_id': currentName,
    },
    UpdateExpression="set #name = :val1 ",
    ExpressionAttributeValues={
        ':val1': newname,
    },
    ExpressionAttributeNames={
    "#name": "name"
    },
    ReturnValues="UPDATED_NEW"
    )
    session["name"] = newname
    #return render_template('main.html')
    
    return response      

##################################################################

@application.route('/changepassword',methods=['GET', 'POST']) 
def changepassword():  
    if request.method == 'GET':
        return render_template('changepassword.html', error = "")
    else:
        request.method == 'POST'
        newPassword = request.form["changepassword"]
        currentUser = session["user_id"]
        upd_password(newPassword, currentUser)
        return render_template('main.html' ,username=session["name"])
        

def upd_password(newPassword, currentUser):
    #print (newname +" "+currentName)
    table = dynamodb.Table("Users")
    response = table.update_item(
    Key={
        'user_id': currentUser,
    },
    UpdateExpression="set #password = :val1 ",
    ExpressionAttributeValues={
        ':val1': newPassword,
    },
    ExpressionAttributeNames={
    "#password": "password"
    },
    ReturnValues="UPDATED_NEW"
    )
    #session["name"] = newname
    #return render_template('main.html')
        
    return response           

@application.route('/home') 
def home():  
    return render_template('home.html')

@application.route('/about') 
def about():  
    return render_template('about.html')

@application.route('/main') 
def main():  
    if session.get('name'):
        return render_template('main.html',username=session["name"])
    else:
        return render_template('home.html')


@application.route('/logout')
def logout():
    session.pop("user_id", None)
    session.pop("name", None)
    return redirect('login')

if __name__ == '__main__':
    application.run(debug=True)
