## Using Sentiment Analysis and CI/CD pipelines for serverless projects.

**Objective**

We will perform the call to Amazon Comprehend with the speech-to-text transcription that we already had to detect 
the Sentiment synchronously, persisting it altogether in the same DynamoDB table.
Because the Amazon Lambda that is listening for created objects in S3 is quite big we will do a refactoring extracting 
part of the code in another Amazon Lambda function that will be triggered from the onComplete SNS topic when 
the Elastic Transcoder is done.  

After that we will create multiple stages with AWS Chalice to be able to test the project in test 
environments separately from production. We will use environment variables to achieve this. Environment 
variables are dynamic variables that we can setup in the terminal or in the system. They can affect the 
way running processes will behave. For example, in our project we will use them to define which services 
(like the database or storage) we are using depending if we are in production or in testing mode. 
Using this we can connect to one or another database, S3 bucket, or SNS topic depending on the variables, 
separating the production and development stages. We will also deploy our project inside AWS CodeCommit and 
create a CI/CD pipeline. We will create custom HTTP responses if an error occurs with AWS Chalice and 
log it in AWS CloudWatch. 


**Workflow**

***1. From the transcription invoke Amazon Comprehend to get the Sentiment and store it in DynamoDB***
Because Amazon Comprehend can do a sync call to determine the sentiment, we can easily do this call before storing it to DynamoDB. 

The result should look like the following in the DynamoDB
![Alt text](images/dynamodb_sentiment_stored.png.png?raw=true "S3 output structure")

***1.1 Refactoring: Using SNS to breack the S3 Event function handler*** 
Because we have the same function listening for events on S3 and because we can only have one function listening on a S3 bucket 
we have that the function handle_audio_created is for both audio and json:
```python
@app.on_s3_event(bucket=AUDIO_MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_audio_created(event):
    if _is_audio(event.key):
        ...
    elif _is_text(event.key):
        ...
      
```
Taking a look a the services we see that Amazon Elastic Transcoder can post to a SNS topic when it's completed, but Amazon Transcribe
doesn't do it. So actually we can create a different function listneing on the SNS topic onComplete and a part from sending a mail we can execute
a lambda function and do the processing of the Audio. 

We can use the @app.on_sns_message(topic=os.environ['TOPIC_NAME']) decorator to listen for it.

To implement it we need to know the json structure that is being posted on the onComplete topic. Actually it's quite easy
since we've configured the same topic to send us an email with the json document as a message. 
So it looks like:

```json
{
  "state": "COMPLETED",
  "version": "2012-09-25",
  "jobId": "1609273710440-ricuek",
  "pipelineId": "1607332673743-ta1eh3",
  "input": {
    "key": "Test/angry2.mp4"
  },
  "inputCount": 1,
  "outputKeyPrefix": "output/",
  "outputs": [
    ...
    {
      "id": "3",
      "presetId": "1351620000001-100110",
      "key": "audio/Test/angry2.mp3",
      "status": "Complete",
      "duration": 134
    },
    ...
  ]
}
```

***2. Create multiple stages with AWS Chalice*** 
Right now we are working always on dev environment, but we want to create 
the production environment.

In the production environment we will use different resources, so we will customize the environment 
variables that we pass in. 

If you are copying the environment variables from the development staging 
it will fail if the S3 buckets are the same from development. There can only be one 
Lambda function subscribed to a S3 bucket. 

***3.Create a CI/CD pipeline with AWS Chalice and AWS CodeCommit***
AWS Chalice has a good support for creating continuous deployment pipelines. 

Once the CloudFormation template has finished creating the stack, you should have several 
new AWS resources that make up a bare bones CD pipeline.

* CodeCommit Repository - The CodeCommit repository is the entrypoint into the pipeline. Any code you want to deploy should be pushed to this remote.
* CodePipeline Pipeline - The CodePipeline is what coordinates the build process, and pushes the released code out.
* CodeBuild Project - The CodeBuild project is where the code bundle is built that will be pushed to Lambda. The default CloudFormation template will create a CodeBuild stage that builds a package using chalice package and then uploads those artifacts for CodePipeline to deploy.
* S3 Buckets - Two S3 buckets are created on your behalf.
    * artifactbucketstore - This bucket stores artifacts that are built by the CodeBuild project. The only artifact by default is the transformed.yaml created by the aws cloudformation package command.
    * applicationbucket - Stores the application bundle after the Chalice application has been packaged in the CodeBuild stage.
* Each resource is created with all the required IAM roles and policies. 

***4.Check if the video file already exists when uploading, and generate an error and an HTTP error response, if so.***   
The best place in the project to do this check is when doign the presigned url call. 
The response that we will send back if the file already exist is a 403 status code and the message
 "The resource you request does already exist".

**Mileston 4: Submit Your Work**

The deliverable is the AWS Chalice Python project.  


**Mileston 4: Solution**

The solution is on ["Milestone 4 Github"](https://github.com/haduart/serverlessbackend-milestone4)

***1. From the transcription invoke Amazon Comprehend to get the Sentiment and store it in DynamoDB***
First we have to give permissions to our Lambda functions to have access to Amazon Comprehend. 
This we can achieve it adding the correct policy in the .chalice/policy-dev.json

```json
  {
      "Effect": "Allow",
      "Action": "comprehend:*",
      "Resource": "*"
    }
```

Also we create some helper functions:
```python
_COMPREHEND_CLIENT = None

def get_comprehend_client():
    global _COMPREHEND_CLIENT
    if _COMPREHEND_CLIENT is None:
        _COMPREHEND_CLIENT = boto3.client('comprehend')
    return _COMPREHEND_CLIENT
```

The easiest way to implement it is on the S3 ObjectCreated Lambda function handle_audio_created, 
and do the sync call just before storing it in DynamoDB.

```python
@app.on_s3_event(bucket=AUDIO_MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_audio_created(event):
    ...
    elif _is_text(event.key):
      ...
      response = get_comprehend_client().detect_sentiment(
                  Text=transcript,
                  LanguageCode='en')
      
              print(json.dumps(response))
      
              try:
                  get_dynamodb_metadata_table().put_item(Item={
                      "JsonFile": event.key,
                      "transcript": transcript,
                      "Sentiment": response["Sentiment"]
                  })
              except Exception as e:
                  print(e)
                  raise NotFoundError("Error adding an element on dynamodb")
```
And this will be the easiest implementation that we can do to do this Sentiment analysis on our 
transcribed video. 

The result should look like the following in the DynamoDB
![Alt text](images/dynamodb_sentiment_stored.png.png?raw=true "S3 output structure")

***1.1 Refactoring: Using SNS to breack the S3 Event function handler*** 
Because we have the same function listening for events on S3 and because we can only have one function listening on a S3 bucket 
we have that the function handle_audio_created is for both audio and json:
```python
@app.on_s3_event(bucket=AUDIO_MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_audio_created(event):
    if _is_audio(event.key):
        ...
    elif _is_text(event.key):
        ...
      
```
Taking a look a the services we see that Amazon Elastic Transcoder can post to a SNS topic when it's completed, but Amazon Transcribe
doesn't do it. So actually we can create a different function listneing on the SNS topic onComplete and a part from sending a mail we can execute
a lambda function and do the processing of the Audio. 

We can use the @app.on_sns_message(topic=os.environ['TOPIC_NAME']) decorator to listen for it.

To implement it we need to know the json structure that is being posted on the onComplete topic. Actually it's quite easy
since we've configured the same topic to send us an email with the json document as a message. 
So it looks like:

```json
{
  "state": "COMPLETED",
  "version": "2012-09-25",
  "jobId": "1609273710440-ricuek",
  "pipelineId": "1607332673743-ta1eh3",
  "input": {
    "key": "Test/angry2.mp4"
  },
  "inputCount": 1,
  "outputKeyPrefix": "output/",
  "outputs": [
    ...
    {
      "id": "3",
      "presetId": "1351620000001-100110",
      "key": "audio/Test/angry2.mp3",
      "status": "Complete",
      "duration": 134
    },
    ...
  ]
}
```
As always we will create an evironment variable on .chalice/config:
```json
"AMAZON_TRANSCODER_ON_COMPLETE_TOPIC": "videopipelineONCOMPLETE",
```

And we will pick it up inside the project:
```python
AMAZON_TRANSCODER_ON_COMPLETE_TOPIC = os.getenv('AMAZON_TRANSCODER_ON_COMPLETE_TOPIC', 'videopipelineONCOMPLETE')
```

Then we will move all the logic for when the mp3 file was created in S3 to the SNS topic lambda dispatcher:
```python
@app.on_sns_message(topic=AMAZON_TRANSCODER_ON_COMPLETE_TOPIC)
def on_audio_is_completed(event):
    print("on_audio_is_completed")

    message = json.loads(event.message)

    output_key_prefix = message['outputKeyPrefix']
    audio_path = output_key_prefix + message['outputs'][2]['key']
    print("audio_path:" + audio_path)

    random_name = str(random.randint(10000, 99999))
    job_name = "JobName" + random_name
    job_uri = "s3://" + AUDIO_MEDIA_BUCKET_NAME + "/" + audio_path
    output_key = audio_path.replace("mp3", "json").replace("audio", "transcribe")
    print("JobName: " + job_name)
    print("job_uri: " + job_uri)
    print("OutputKey: " + output_key)
    get_transcribe_client().start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaSampleRateHertz=44100,
        MediaFormat='mp4',
        LanguageCode='en-US',
        OutputBucketName=AUDIO_MEDIA_BUCKET_NAME,
        OutputKey=output_key,
    )

    status = get_transcribe_client().get_transcription_job(TranscriptionJobName=job_name)
    print(status)
    return {'transcribe': job_name}
``` 

***2. Create multiple stages with AWS Chalice*** 
Right now we are working always on dev environment, but we want to create 
the production environment.

In the production environment we will use different resources, so we will customize the environment 
variables that we pass in. 

First we will modify the .chalice/config.json to add the production (prod) stage:

```json
  "stages": {
    "dev": {
      "api_gateway_stage": "api",
      "environment_variables": {
        "RESPONSES_TABLE_NAME": "responsesDEV",
        "AMAZON_TRANSCODER_ON_COMPLETE_TOPIC": "videopipelineONCOMPLETEdev",
        "METADATA_TABLE_NAME": "metadataDEV",
        "MEDIA_BUCKET_NAME": "dev.videos.oico.com",
        "AUDIO_MEDIA_BUCKET_NAME": "dev.outputvideos.oico.com",
        "PIPELINE_NAME": "1607332673743-ta34rt"
      }
    },
    "prod": {
      "api_gateway_stage": "api",
      "environment_variables": {
        "RESPONSES_TABLE_NAME": "responses",
        "AMAZON_TRANSCODER_ON_COMPLETE_TOPIC": "videopipelineONCOMPLETE",
        "METADATA_TABLE_NAME": "metadata",
        "MEDIA_BUCKET_NAME": "videos.oico.com",
        "AUDIO_MEDIA_BUCKET_NAME": "outputvideos.oico.com",
        "PIPELINE_NAME": "1607332673743-ta1eh3"
      }
    }
  }
```
Since we are using a custom policy we have to create the .chalice/policy-prod.json

To deploy the production staging instead of the development the command will be the following:
```commandline
chalice deploy --stage prod
```

If you are copying the environment variables from the development staging 
it will fail if the S3 buckets are the same from development. There can only be one 
Lambda function subscribed to a S3 bucket. 

***3.Create a CI/CD pipeline with AWS Chalice and AWS CodeCommit***
AWS Chalice has a good support for creating continuous deployment pipelines. 

Once the CloudFormation template has finished creating the stack, you should have several 
new AWS resources that make up a bare bones CD pipeline.

* CodeCommit Repository - The CodeCommit repository is the entrypoint into the pipeline. Any code you want to deploy should be pushed to this remote.
* CodePipeline Pipeline - The CodePipeline is what coordinates the build process, and pushes the released code out.
* CodeBuild Project - The CodeBuild project is where the code bundle is built that will be pushed to Lambda. The default CloudFormation template will create a CodeBuild stage that builds a package using chalice package and then uploads those artifacts for CodePipeline to deploy.
* S3 Buckets - Two S3 buckets are created on your behalf.
    * artifactbucketstore - This bucket stores artifacts that are built by the CodeBuild project. The only artifact by default is the transformed.yaml created by the aws cloudformation package command.
    * applicationbucket - Stores the application bundle after the Chalice application has been packaged in the CodeBuild stage.
* Each resource is created with all the required IAM roles and policies. 

```commandline
$ chalice generate-pipeline --pipeline-version v2 pipeline.json
$ aws cloudformation deploy --stack-name mystack --template-file pipeline.json --capabilities CAPABILITY_IAM

Waiting for changeset to be created..
Waiting for stack create/update to complete
Successfully created/updated stack - mystack
```

***4.Check if the video file already exists when uploading, and generate an error and an HTTP error response, if so.***
The best place in the project to do this check is when doign the presigned url call. 
The response that we will send back if the file already exist is a 403 status code and the message
 "The resource you request does already exist".

There are multiple ways to check if a file already exist in S3 but this is one of the fastest:

```python
def check_if_file_exists(file_name):
    try:
        get_s3_client().head_object(Bucket=MEDIA_BUCKET_NAME, Key=file_name)
    except ClientError as e:
        print("The file does not exist")
        return False
    else:
        print("The file exist")
        return True
```

The HEAD operation retrieves metadata from an object without returning 
the object itself. This operation is useful if you're only interested in 
an object's metadata.

Then in the presigned url call we will check if the file already exist before generating the presigend url:

```python



@app.route('/presignedurl/{project}/{step}', methods=['GET'], cors=cors_config)
def presigned_url(project, step):
    ...
    new_user_video = project + "/" + str(step_number) + "/" + hexmail + '.webm'
    if check_if_file_exists(new_user_video):
        return Response(body="The resource you requested does already exist",
                        status_code=403,
                        headers={'Content-Type': 'text/plain'})

    ...
```

**Importance to project**    
In this project we've seen how to use advance ML services in AWS like Amazon Comprehend
and how to integrate them in our own projects. We've also seen how to extract code in 
a serverless project, using other events that are dispatched so we have smaller Amazon Lambda 
functions. 

Finally, we've created different stages, one for production and another for development. And we've seen 
how to pass specific data for each stage through environment variables. Also we've seen how we can easily 
create a CI/CD environment for our project with AWS Chalice, that allow us to easily create
a CodeCommit Repository, a CodePipeline Pipeline, a CodeBuild Project and also extra S3 buckets to 
store the generated artifacts. 


**Takeaways**
* Hands-on experience with Amazon Comprehend for Sentiment Analysis. 
* Experience with DynamoDB streams.
* Manually configuring to dispatch events when data is added/updated or deleted.
* Manually attaching a Lambda Function in AWS Chalice.  
* Create multiple stages with AWS Chalice
* Create and use environment variables in AWS Chalice
* Setup and use AWS CodeCommit
* Create CI/CD pipelines
* Diagnose errors in with AWS CloudWatch.
 
**Resources**

* [Amazon Comprehend](https://aws.amazon.com/comprehend/)
* [Amazon Comprehend Boto3 Detect Sentiment](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/comprehend.html#Comprehend.Client.detect_sentiment)
* [AWS Chalice Stages](https://aws.github.io/chalice/topics/stages.html)
* [AWS Chalice Continuous Deployment](https://aws.github.io/chalice/topics/cd.html)
* [AWS Chalice CloudFormation Support](https://aws.github.io/chalice/topics/cfn.html)
