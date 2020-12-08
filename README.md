## Creating video processing pipelines using event based architectures.

**Objective**

After a video is uploaded to S3, S3 dispatches an event that will trigger an AWS Lambda function that will transcode 
the video into a lower bitrate. We will also add DynamoDB to store the information about the user who uploaded the video,
the name of the video, and the bucket and folder where it is located.
Because we like writing clean code we will introduce testing to secure and validate the project implementation, 
including unit and integration tests.  
  

**Workflow**

***1. Connect the routes with DynamoDB using Python Botocore to store and retrieve the user and video information from a real database instead of an in-memory structure.***
We want to connect to DynamoDB to store the necessary data for our project. The DynamoDB table should look like the following:

![Alt text](docs/images/dynamodb-table.png?raw=true "DynamoDB Table")

We will name this table *responses*

To make it simpler but still introduccing a persistence layer let's store the information whenever some askes for a presigned url.
In the form of /presignedurl/testProject/0/?mail=eduard@orkei.com&project=Test&step=0
Where *testProject* will be the route param *project* and in this case *0* will be the *step*. We want to stored as a composed 
key in dynamoDB. (Check the table "DynamoDB Table") 

Refactor the code so when we invoke the /videos url we fetch all the items. 
  
***2. Create an AWS Elastic Transcoder pipeline that handles all the transcoding jobs to create a lower resolution video.***

>Amazon Elastic Transcoder is media transcoding in the cloud. It is designed to be a highly scalable, easy to use and a 
cost effective way for developers and businesses to convert (or *transcode*) media files from their source format into 
versions that will playback on devices like smartphones, tablets and PCs.

*[AWS Elastic Transcoder Documentation](https://aws.amazon.com/elastictranscoder/)*

In AWS Elastic Transcoder there are three elements: Pipelines, Presets and Jobs.  
Presets is the configuration that will be performed on the transcode operation. In our case we want lower resolution. 
We will use a predefined configuration (preset) that is called *web* that converts the resolution to 1280x720. 

A 3 minute mobile video shot with a Samsung S9+ has a resolution of 1920 × 1080 and its size is 355 MB. 
After lowering the resolution to 1280x720 which is still HD, its size is 55 MB.

The *Pipeline* is what we have to create in this step, is where we describe which S3 Buckets will be used for input and 
output of the videos. As a good practice the output bucket, where the transcoded videos, audios and thumbnails images 
will be stored, should be different that the input bucket with the original uploaded videos. 

![Alt text](docs/images/created-pipeline.png?raw=true "Elastic Transcoder Pipeline")
   
  
***3. Create a new function in AWS Chalice that is triggered when a file is stored in S3.***
      * This function will write this new file in DynamoDB, it will create a transcoder job that will be executed in the 
      Amazon Elastic Transcoder pipeline that we previously created, storing the new transcoded video back in S3.           

For that there's a special annotation in AWS Chalice to mark that a function will be triggered by an S3 Event. 
```python
@app.on_s3_event(bucket=MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
``` 

***4. Setup Pytests and create our first unit tests***    
        
***5. Create integration tests***

In AWS Chalice we can use fixture to setup an integration test. 

```python
from pytest import fixture
```
   

**Mileston 2: Submit Your Work**

The deliverable is the AWS Chalice Python project.  


**Mileston 2: Solution**

The solution is on ["Milestone 2 Github"](https://github.com/haduart/serverlessbackend-milestone2)

***1. Connect the routes with DynamoDB using Python Botocore to store and retrieve the user and video information from a real database instead of an in-memory structure.***

First we create the DynamoDB table where we will story the video responses that we are collecting.
The main keys will be "Project", that is a String, "Step" that in case of having multiple interactions in that project 
it will store its value as a number. Finally, the mail of the user that has uploaded a video for that Project and Step.

```commandline
$ aws cloudformation create-stack --stack-name dynamodb-oico --capabilities CAPABILITY_IAM --template-body file://cloudformation/dynamodb.yml
```
Then in the project we will get the table name by environment variables, setting different values depending on the stage that we are working on. So the .chalice/config.json will look like:
```json
{
"stages": {
    "dev": {
      "api_gateway_stage": "api",
      "environment_variables": {
        "RESPONSES_TABLE_NAME": "responses"
      }
    }
  }
}
```

In the project we will pick up this variable, and we will use boto3 dynamodb sdk to interact with it:
```python
import os
import boto3

RESPONSES_TABLE_NAME = os.getenv('RESPONSES_TABLE_NAME', 'defaultTable')

response_data_table = boto3.resource('dynamodb').Table(RESPONSES_TABLE_NAME)
```

To start making the code nicer we will use global variable to cache the boto sdk connections:
```python
_DYNAMODB_CLIENT = None
_DYNAMODB_TABLE = None

RESPONSES_TABLE_NAME = os.getenv('RESPONSES_TABLE_NAME', 'defaultTable')

def get_dynamodb_table():
    global _DYNAMODB_TABLE
    global _DYNAMODB_CLIENT
    if _DYNAMODB_TABLE is None:
        _DYNAMODB_CLIENT = boto3.resource('dynamodb')
        _DYNAMODB_TABLE = _DYNAMODB_CLIENT.Table(RESPONSES_TABLE_NAME)
    return _DYNAMODB_TABLE
```

Now when we ask for a presigned URL this information will be stored in the database:
```python
# GET /presignedurl/testProject/0/?mail=eduard@orkei.com&project=Test&step=0
@app.route('/presignedurl/{project}/{step}', methods=['GET'], cors=cors_config)
def presigned_url(project, step):
    if app.current_request.query_params is None:
        raise NotFoundError("No parameter has been sent")

    mail = app.current_request.query_params.get('mail')
    if len(mail) == 0:
        raise NotFoundError("mail is empty")
    print("query_param mail: " + mail)

    if project is None or len(project) == 0:
        raise NotFoundError("project is empty")
    print("query_param project: " + project)

    step_number = 0
    if step is not None or len(step) > 0:
        try:
            step_number = int(step)
        except ValueError:
            print("query_param v is not a number: " + step)
            step_number = 0
    print("query_param step: " + step)

    h = blake2b(digest_size=10)
    byte_mail = bytes(mail, 'utf-8')
    h.update(byte_mail)
    hexmail = h.hexdigest()
    print("hex mail: " + hexmail)

    new_user_video = project + "/" + str(step_number) + "/" + hexmail + '.webm'

    try:
        get_dynamodb_table().put_item(Item={
            "ProjectStep": project + "-" + str(step_number),
            "Mail": mail,
            "video": new_user_video
        })
    except Exception as e:
        print(e)
        raise NotFoundError("Error adding an element on dynamodb")

    try:
        response = get_s3_client().generate_presigned_post(Bucket="videos.oico.com",
                                                           Key=new_user_video,
                                                           Fields={"acl": "public-read"},
                                                           Conditions=[{
                                                               'acl': 'public-read'
                                                           }],
                                                           ExpiresIn=3600)
    except ClientError as e:
        logging.error(e)
        raise BadRequestError("Internal Error generating presigned post ")
    return response
```

We will refactor de /videos call to fetch the information from DynamoDB:
```python
# /videos/?mail=eduard@orkei.com
@app.route('/videos', methods=['GET'], authorizer=basic_auth)
def videos():
    app.log.debug("GET Call app.route/videos")
    mail = app.current_request.query_params.get('mail')

    if len(mail) == 0:
        raise NotFoundError("mail is empty")

    response = get_dynamodb_table().query(
        KeyConditionExpression=Key('ProjectStep').eq('Alba-0')
    )
    items = response['Items']
    print(items)

    return json.dumps(items)
```

If we want to test DynamoDB from the command line AWS CLI we can use the following commands:

Count all items at DeviceData
```commandline
aws dynamodb scan --table-name responses --select "COUNT"
```

Getting all elements that had the extended Keep Alive
```commandline

aws dynamodb scan \
  --table-name responses \
  --filter-expression "attribute_exists(video)"

aws dynamodb scan  \
 --table-name responses  \
--filter-expression "Mail = :mail"  \
--expression-attribute-values '{":mail" : {"S":"eduard@orkei.com"}}' 
```

***2. Create an AWS Elastic Transcoder pipeline that handles all the transcoding jobs to create a lower resolution video.*** 

***3. Create a new function in AWS Chalice that is triggered when a file is stored in S3.***    

Before using a new service like AWS Elastic Transcoder let's remember to give permissions to our *Lambda function* within
Chalice to have access to it. So like we did to access S3 we have to add custom policy permissions in our project. 
For that we have to include the following rules in *.chalice/policy-dev.json*

```json
{
      "Effect": "Allow",
      "Action": "elastictranscoder:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "sns:*",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "dynamodb:*",
      "Resource": "*"
    },
```
 
Capturing a S3 Event in AWS Chalice is quite simple:
```python
@app.on_s3_event(bucket=MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_object_created(event):
    print("handle_object_created: " + event.key)
    if _is_video(event.key):
        print("Correct video uploaded: " + event.key)
        transcoder_video(event.key)
```
For transcoding a video we will use elastictranscoder boto3 SDK. We will create a new job for each new video that we 
want to transcode with the correct parameters that will be chosing the right pipeline ID already created in the previous 
step, and choosing the preset or presets that we want to use. In our case we want to use the System Preset Web, which 
id is *'1351620000001-100070'*

```python
def transcoder_video(input_file):    
    pipeline_id = PIPELINE_NAME  
    output_file = input_file  # Desired root name of the transcoded output files

    output_file_prefix = 'output/'  # Prefix for all output files

    system_preset_web_preset_id = '1351620000001-100070'
    
    outputs = [
        {
            'Key': 'web/' + output_file,
            'PresetId': system_preset_web_preset_id
        }
    ]

    # Create a job in Elastic Transcoder
    job_info = create_elastic_transcoder_job(pipeline_id,
                                             input_file,
                                             outputs, output_file_prefix)
    if job_info is None:
        print("job_info has failed!!!!")

    # Output job ID and exit. Do not wait for the job to finish.
    print(f'Created Amazon Elastic Transcoder job {job_info["Id"]}')
``` 
Once we have the parameters right is just invoking the boto SDK correctly:

```python
def create_elastic_transcoder_job(pipeline_id, input_file,
                                  outputs, output_file_prefix):
    try:
        response = get_elastictranscoder_client().create_job(PipelineId=pipeline_id,
                                                             Input={'Key': input_file},
                                                             Outputs=outputs,
                                                             OutputKeyPrefix=output_file_prefix)
    except ClientError as e:
        print(f'ERROR: {e}')
        return None
    return response['Job']
```
Take into account that the output file will be the same as the input one in this example. With all the subfolder. 

![Alt text](docs/images/transcoded-S3-output-sample.png?raw=true "Example of the Elastic Transcoder output structure in S3")

***4. Setup Pytests and create our first unit tests***   

First install the library pytest to create the tests. We don't have to added it in the requirements 
since it's not something that we want to deploy within our Lambda function. 

```commandline
$ pip install pytest

$ pytest

================== test session starts ================== 
platform darwin -- Python 3.7.3, pytest-6.1.2, py-1.9.0, pluggy-0.13.1
rootdir: /Users/haduart/Documents/serverlessbackend
collected 0 items                                                                                                                                                          

================== no tests ran in 0.03s ================== 
``` 
To create our first test we create a file named test_app.py. Because it starts with test_ python 
knows that it's a test. 
     
***5. Create integration tests***
To create integration tests we use pytest fixtures for that. 

```python
from pytest import fixture
import app
from basicauth import decode, encode
import json

@fixture
def api():
    from chalice.local import LocalGateway
    from chalice.config import Config
    return LocalGateway(app.app, Config())
```

Once we have created or testing api we can pass it in our testing functions to be able tot test requests. For example 
we will test if we are authorized or not. 
```python
def test_root_path(api):
    response = api.handle_request(method='GET', path='/', body=None, headers={})
    assert 200 == response['statusCode']
    assert {'hello': 'world'} == json.loads(response['body'])


def test_basic_authentication(api):
    autorization = {'Authorization': encode("edu", "edu")}
    response = api.handle_request(method='GET', path='/hello', body=None, headers=autorization)
    assert 200 == response['statusCode']

```

**Importance to project**

In this project we have experienced the first *Event Driven Architecture*, handling an event after a file is being uploaded 
in S3 and doing a processing on it in an asynchronous way.

We have also added a database layer to our project, using a *NoSQL* database like *DynamoDB*.

Finally, we've start setting up PyTest tooling to be able to test our project using unit testing and integration testing.         

**Takeaways**
* How to capture triggered events with Lambda functions within an AWS Chalice project.
* Hands-on experience with Amazon Elastic Transcoder pipelines, jobs, and presets, and how they can be automated using AWS Lambda functions.
* Hands-on experience with DynamoDB, query, insert, and update with Python and Botocore Library.
* Experience testing with both Unit and Integration tests. 


**Resources**

***DynamoDB***

* [How to add data in DynamoDB with Boto3](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.03.html#GettingStarted.Python.03.01)
* [Working with Queries in DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)
* [Best Practices for DynamodDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices.html)
* [Working with Scans](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html) 
* [Scans ConditionExpressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
* [Choosing the Right DynamoDB Partition Key](https://aws.amazon.com/es/blogs/database/choosing-the-right-dynamodb-partition-key/)

***S3***

* [AWS Chalice: Add S3 event source](https://chalice-workshop.readthedocs.io/en/latest/media-query/04-s3-event.html)

***ElasticTranscoder***
* [ElasticTranscoder: Notifications of Job Status](https://docs.aws.amazon.com/elastictranscoder/latest/developerguide/notifications.html)
* [Controlling Access to ElasticTranscoder](https://docs.aws.amazon.com/elastictranscoder/latest/developerguide/access-control.html)

***Python Test***
* [Testing AWS Chalice](https://aws.github.io/chalice/topics/testing.html)
