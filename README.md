## Creating video processing pipelines using event based architectures.

**Objective**

* After a video is uploaded to S3, S3 dispatches an event that will trigger an AWS Lambda function that will transcode the video into a lower bitrate. We will also add DynamoDB to store the information about the user who uploaded the video, the name of the video, and the bucket and folder where it is located. Because we like writing clean code we will add tests to secure and validate the project implementation, including unit and integration tests.  
  

**Workflow**

1. Connect the routes with DynamoDB using Python Botocore to store and retrieve the user and video information from a real database instead of an in-memory structure.  
2. Create an AWS Elastic Transcoder pipeline that handles all the transcoding jobs to create a lower resolution video.    
3. Create a new function in AWS Chalice that is triggered when a file is stored in S3.
    * This function will write this new file in DynamoDB, it will create a transcoder job that will be executed in the Amazon Elastic Transcoder pipeline that we previously created, storing the new transcoded video back in S3. For the transcoding, we will use a predefined configuration (preset) that is called web that converts the resolution to 1280x720. A 3 minute mobile video shot with a Samsung S9+ has a resolution of 1920 × 1080 and its size is 355 MB. After lowering the resolution to 1280x720 which is still HD, its size is 55 MB.
4. Setup Pytests and create our first unit tests        
5. Create integration tests
   

**Mileston 2: Submit Your Work**

The deliverable is the AWS Chalice Python project.  


**Mileston 2: Solution**

The solution is on ["Milestone 2 Github"](https://github.com/haduart/serverlessbackend-milestone2)

***1. Connect the routes with DynamoDB using Python Botocore to store and retrieve the user and video information from a real database instead of an in-memory structure.***

First we create the DynamoDB table where we will story the video responses that we are collecting.
The main keys will be "Project", that is a String, "Step" that in case of having multiple interactions in that project it will store its value as a number. And finally the mail of the user that has upload a video for that Project and Step. 
 
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


Counting all items at DeviceData
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

This function will write this new file in DynamoDB, it will create a transcoder job that will be executed in the Amazon Elastic Transcoder pipeline that we previously created, storing the new transcoded video back in S3. For the transcoding, we will use a predefined configuration (preset) that is called web that converts the resolution to 1280x720. A 3 minute mobile video shot with a Samsung S9+ has a resolution of 1920 × 1080 and its size is 355 MB. After lowering the resolution to 1280x720 which is still HD, its size is 55 MB.

***4. Setup Pytests and create our first unit tests***   
     
***5. Create integration tests***


**Importance to project**

*      

**Takeaways**
* How to capture triggered events with Lambda functions within an AWS Chalice project.
* Hands-on experience with Amazon Elastic Transcoder pipelines, jobs, and presets, and how they can be automated using AWS Lambda functions.
* Hands-on experience with DynamoDB, query, insert, and update with Python and Botocore Library.
* Experience testing with both Unit and Integration tests. 


**Resources**
* [How to add data in DynamoDB with Boto3](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GettingStarted.Python.03.html#GettingStarted.Python.03.01)
* [Working with Queries in DynamoDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Query.html)
* [AWS Chalice: Add S3 event source](https://chalice-workshop.readthedocs.io/en/latest/media-query/04-s3-event.html)

* [Best Practices for DynamodDB](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/BestPractices.html)
* [Working with Scans](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Scan.html) 
* [Scans ConditionExpressions](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
* [Choosing the Right DynamoDB Partition Key](https://aws.amazon.com/es/blogs/database/choosing-the-right-dynamodb-partition-key/)
