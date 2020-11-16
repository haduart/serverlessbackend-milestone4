## Securely upload videos to S3 using a serverless architecture

**Objective**

* Using AWS Chalice, we will generate and send to the client a pre-signed URL that can be used to upload a file directly to S3. An S3 bucket and folder structure will be created for uploaded files. It is essential to protect the privacy of our users and data, so we will test security and authentication methods. 
  

**Workflow**

1. Setup and configure AWS CL  
2. Install and setup AWS Chalice    
3. Create first project with Chalice
    * Create a python virtual environment
4. Add Python libraries and AWS botocore    
    * save the python libraries into a requirements.txt file with pip freeze.
5. Create an S3 Bucket
   *  Modify the .chalice/config.json to give custom policy permissions to the lambda functions to write to S3
   *  Add the custom policy in .chalice/policy-dev.json to run for the dev staging.
   *  To allow full access to S3 from the lambdas use the following policy: 
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [    
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents"
         ],
         "Resource": "arn:aws:logs:*:*:*"
       },
       {
         "Effect": "Allow",
         "Action": "s3:*",
         "Resource": "*"
       }
     ]
   }
    ```
6. Build logic for generating the presigned-url as a URL get request on the /presignedurl endpoint.
   * use the boto3 client library ```boto3.client('s3') ```
   * use the generate_presigned_post method. 
   * pass the mail as a query parameter to know who wants to upload the video. ```GET /presignedurl?mail=eduard@orkei.com ```
   * when generating a presigned url we have to specify the name of the file that will be stored in S3, the end name. For that one simple way is to hash the mail of the user requesting the presigned url:
   ```python
   from hashlib import blake2b
   
   h = blake2b(digest_size=10)
   byte_mail = bytes(mail, 'utf-8')
   h.update(byte_mail)
   hexmail = h.hexdigest()
   print("hex mail: " + hexmail)
   ``` 
   
7. Add security and authentication. We want to implement a basic security where if we just pass the same user as a password it should allow us access to it.
   * use the basicauth pip package.
   * The app autorizers works with annotations: 
   ``` @app.autorizer()``` and it returns an AuthResponse allowing specific access to routes and methods:  ```return AuthResponse(routes=[AuthRoute('/*', ["GET", "POST"])]```
    
8. Add extra routes. We will retrieve and store the information in-memory inside AWS Chalice project. We will create a "secure" endpoint to check how many videos has one user uploaded in our platform. The endpoint it will be /videos and we will pass the mail as a query param  
   * In case the user is authenticated (from the basic auth) and it exists in our data structure we will return all the videos that we have from him:
   ```python
   users_video_dictionary = {
       "eduard@orkei.com": ["eduard-hashed.mp4", "eduard-hashed1.mp4", "eduard-hashed2.mp4"]
   }
    ```
   For that we will count the videos that the user (by email) has asked a presigned url for, and we will add this counter as the last string in the hashed video:
   ```python
   str_count = ""
   if mail in users_video_dictionary:
      str_count = str(len(users_video_dictionary[mail]))
   
   new_user_video = hexmail + str_count + '.mp4'
       users_video_dictionary[mail].append(new_user_video) 
   ```
   

**Mileston 1: Submit Your Work**

The deliverable is the AWS Chalice Python project.  


**Mileston 1: Solution**

First of all you have to check that you are using Python 3, ideally Python 3.7 or higher. 
```commandline
$ python3 --version
Python 3.7.3 
```
If you don't have it install it:
```commandline
 $ sudo port install python37
 $ sudo port select --set python python37
```

****1. Setup and configure AWS CLI****

```commandline
 $ sudo python -m pip install awscli
 $ aws configure --profile yourproject
 AWS Access Key ID [None]: AKIAJG7SD45V########
 AWS Secret Access Key [None]: Tmc0K0o+OF5Y0Dfecwg4#############
 Default region name [None]: eu-west-1  
 Default output format [None]: json
 
 $ aws ec2 describe-instances --profile yourproject
 {
     "Reservations": []
 }
 
 $ export AWS_PROFILE=yourproject
 $ aws s3 ls
 2020-10-27 10:36:04 app.yourproject.io
```  

****2. Install and setup AWS Chalice****

```commandline
$ python3 -m pip install chalice
```

****3. Create first project with Chalice****

```commandline
$ chalice new-project serverlessbackend
$ cd serverlessbackend
```
****4. Add Python libraries and AWS botocore****

Creating virtual environment
```commandline
$ python3 -m venv .chalice/venv37
$ ./chalice/venv32/bin/activate
```
Installing packages
```commandline
$ pip install chalice
$ pip list
Package         Version
--------------- -------
attrs           20.2.0 
botocore        1.19.16
chalice         1.21.4 
click           7.1.2  
enum-compat     0.0.3  
jmespath        0.10.0 
mypy-extensions 0.4.3  
pip             19.0.3 
python-dateutil 2.8.1  
PyYAML          5.3.1  
setuptools      40.8.0 
six             1.15.0 
urllib3         1.25.11
wheel           0.35.1 
```
Installing AWS Boto3
```commandline
$ pip install boto3
```
Saving pip packages in the requirements
```commandline
$ pip freeze --local > requirements.txt
```
Deploy project
```commandline
$ chalice deploy
Creating deployment package.
Creating IAM role: serverlessbackend-dev
Creating lambda function: serverlessbackend-dev
Creating Rest API
Resources deployed:
  - Lambda ARN: arn:aws:lambda:eu-west-1:######:function:serverlessbackend-dev
  - Rest API URL: https://k3qj####.execute-api.eu-west-1.amazonaws.com/api/
```

****5. Create an S3 Bucket****

Once we have the s3 bucked created we will have to change the configuration so that our chalice function can access S3. 
In AWS this is done through security policies. We put our custom policy in our project:
```commandline
$ cat .chalice/policy-dev.json
```
```json
{
  "Version": "2012-10-17",
  "Statement": [    
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": "s3:*",
      "Resource": "*"
    }
  ]
}
```
Also, to be able to use our own policy we have to disable the autogenerated policy from AWS Chalice. That is changing the configuration in .chalice/config.json:
```json
{
  "version": "2.0",
  "app_name": "serverlessbackend",
  "autogen_policy": false,
  "tags": [
    {
      "project": "serverless"
    }
  ],
  "stages": {
    "dev": {
      "api_gateway_stage": "api"
    }
  }
}
```

***6. Build logic for generating the presigned-url as a URL get request.***

For the presigned-url we want to create a simple  url that we can get with the proper parameters and it returns us the necessary keys so that we can upload the video in a secure way to S3.
Our handler will be on /presigendurl and we will expect the parameter mail to generate a temporary signed url:

The python code will look like:
```python
# GET /presignedurl?mail=eduard@orkei.com
@app.route('/presignedurl', methods=['GET'], cors=cors_config)
def presigned_url():
    mail = app.current_request.query_params.get('mail')

    print("query_param mail: " + mail)

    if len(mail) == 0:
        raise NotFoundError("mail is empty " + mail)

    h = blake2b(digest_size=10)
    h.update(b'Replacing SHA1 with the more secure function')
    hexmail = h.hexdigest()
    print("hex mail: " + hexmail)

    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(Bucket="videos.serverless.com",
                                                     Key=hexmail + '.mp4',
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
We will have to import the following libraries:
```python
import boto3
from hashlib import blake2b
```

So when we execute the call to the presigned URL
```commandline
$ curl https://k3#####ia.execute-api.eu-west-1.amazonaws.com/api/presignedurl?mail=eduard@orkei.com
```

Whe receive a json response as follows:
```json
{
  "url": "https://s3.eu-west-1.amazonaws.com/videos.serverless.com",
  "fields": {
    "acl": "public-read",
    "key": "79c8dc#####71e4b.mp4",
    "AWSAccessKeyId": "ASIAY###4CH7K6J6",
    "x-amz-security-token": "IQoJb3JpZ##########V1LXdlc3QtMSJHMEUCIENgnkBRElrJifvlykxEoVmb3+l0M24Z4GkHTdvUvf8vAiEAqrk4UqYRpvm684Tq2jR9t7AAMhM/Xu5g+D/S+q6WOaUq3QEIrf//////////ARABGgw1OTE0MTAzODk3MDciDG3UvOtcNudbsAAu2iqxAcxDq6Cje4iG5mtphJ9WQMknzrtwtZCWcKuMYkL2umAkk3bAbnjeut/LUH0FlpaNzv7Uci0udhFW6lRs0q+lY2GXO2pLeWIh+CNObfQ5FiKdGJ4UM5SY0Sr8KkMbZmbKHLuy2jBzfglkU3G8P9QqKz+7sV7gUNnvRrTp7cKeRUu4zyIKncHpJunqNA4jhJF2mhHZix90N5nUtCM/mU6p+AKn70pTMc95ESVOlNOiqbJbFzCItLb9BTrgAdPhA5Vgq2cUXTImwqen/eaz7pnEOGStdTWLEkf9OTN9sslt97makyuPpu2Qwp8VjiYbqtyflmVMrv3C1Lvmb76prcaq8vNZuFKkfaWHQ/E033881S8PWP7+s+armrAjFUn5Diy/gnBtHWtw7cUU9DmwyZW5g2xq438XAKePx/zisY+zjf3fXB24jmWwSYYYG7ycxfZuCNcgGjpqxWV29VJ7QLmqEvf73g98Ysnp/WtjYiCQUQlGUMxKDIszQ5C3Hl4ZurKoRTg7JDne54YNWJq0wRnYlSSaJVo9DW85ax+t",
    "policy": "eyJleHBpcmF################TJUMjE6MjQ6NDJaIiwgImNvbmRpdGlvbnMiOiBbeyJhY2wiOiAicHVibGljLXJlYWQifSwgeyJidWNrZXQiOiAidmlkZW9zLm9pY28uY29tIn0sIHsia2V5IjogIjc5YzhkY2I2NTFmNWI3MDcxZTRiLm1wNCJ9LCB7IngtYW16LXNlY3VyaXR5LXRva2VuIjogIklRb0piM0pwWjJsdVgyVmpFRVVhQ1dWMUxYZGxjM1F0TVNKSE1FVUNJRU5nbmtCUkVsckppZnZseWt4RW9WbWIzK2wwTTI0WjRHa0hUZHZVdmY4dkFpRUFxcms0VXFZUnB2bTY4NFRxMmpSOXQ3QUFNaE0vWHU1ZytEL1MrcTZXT2FVcTNRRUlyZi8vLy8vLy8vLy9BUkFCR2d3MU9URTBNVEF6T0RrM01EY2lERzNVdk90Y051ZGJzQUF1MmlxeEFjeERxNkNqZTRpRzVtdHBoSjlXUU1rbnpydHd0WkNXY0t1TVlrTDJ1bUFrazNiQWJuamV1dC9MVUgwRmxwYU56djdVY2kwdWRoRlc2bFJzMHErbFkyR1hPMnBMZVdJaCtDTk9iZlE1RmlLZEdKNFVNNVNZMFNyOEtrTWJabWJLSEx1eTJqQnpmZ2xrVTNHOFA5UXFLeis3c1Y3Z1VObnZSclRwN2NLZVJVdTR6eUlLbmNIcEp1bnFOQTRqaEpGMm1oSFppeDkwTjVuVXRDTS9tVTZwK0FLbjcwcFRNYzk1RVNWT2xOT2lxYkpiRnpDSXRMYjlCVHJnQWRQaEE1VmdxMmNVWFRJbXdxZW4vZWF6N3BuRU9HU3RkVFdMRWtmOU9UTjlzc2x0OTdtYWt5dVBwdTJRd3A4VmppWWJxdHlmbG1WTXJ2M0MxTHZtYjc2cHJjYXE4dk5adUZLa2ZhV0hRL0UwMzM4ODFTOFBXUDcrcythcm1yQWpGVW41RGl5L2duQnRIV3R3N2NVVTlEbXd5Wlc1ZzJ4cTQzOFhBS2VQeC96aXNZK3pqZjNmWEIyNGptV3dTWVlZRzd5Y3hmWnVDTmNnR2pwcXhXVjI5Vko3UUxtcUV2ZjczZzk4WXNucC9XdGpZaUNRVVFsR1VNeEtESXN6UTVDM0hsNFp1cktvUlRnN0pEbmU1NFlOV0pxMHdSbllsU1NhSlZvOURXODVheCt0In1dfQ==",
    "signature": "ZEzZZao#######GYiE2mTgM="
  }
}
```

And with this response we can upload a video file, for example an intro.mp4:
```commandline
$ curl -X POST  -F "acl=public-read" \
     -F "key=79c8dcb651f5b7071e4b.mp4" \
     -F "AWSAccessKeyId=#######F4CH7K6J6" \
     -F "x-amz-security-token=################dlc3QtMSJHMEUCIENgnkBRElrJifvlykxEoVmb3+l0M24Z4GkHTdvUvf8vAiEAqrk4UqYRpvm684Tq2jR9t7AAMhM/Xu5g+D/S+q6WOaUq3QEIrf//////////ARABGgw1OTE0MTAzODk3MDciDG3UvOtcNudbsAAu2iqxAcxDq6Cje4iG5mtphJ9WQMknzrtwtZCWcKuMYkL2umAkk3bAbnjeut/LUH0FlpaNzv7Uci0udhFW6lRs0q+lY2GXO2pLeWIh+CNObfQ5FiKdGJ4UM5SY0Sr8KkMbZmbKHLuy2jBzfglkU3G8P9QqKz+7sV7gUNnvRrTp7cKeRUu4zyIKncHpJunqNA4jhJF2mhHZix90N5nUtCM/mU6p+AKn70pTMc95ESVOlNOiqbJbFzCItLb9BTrgAdPhA5Vgq2cUXTImwqen/eaz7pnEOGStdTWLEkf9OTN9sslt97makyuPpu2Qwp8VjiYbqtyflmVMrv3C1Lvmb76prcaq8vNZuFKkfaWHQ/E033881S8PWP7+s+armrAjFUn5Diy/gnBtHWtw7cUU9DmwyZW5g2xq438XAKePx/zisY+zjf3fXB24jmWwSYYYG7ycxfZuCNcgGjpqxWV29VJ7QLmqEvf73g98Ysnp/WtjYiCQUQlGUMxKDIszQ5C3Hl4ZurKoRTg7JDne54YNWJq0wRnYlSSaJVo9DW85ax+t" \
     -F "policy=#############ogIjIwMjAtMTEtMTJUMjE6MjQ6NDJaIiwgImNvbmRpdGlvbnMiOiBbeyJhY2wiOiAicHVibGljLXJlYWQifSwgeyJidWNrZXQiOiAidmlkZW9zLm9pY28uY29tIn0sIHsia2V5IjogIjc5YzhkY2I2NTFmNWI3MDcxZTRiLm1wNCJ9LCB7IngtYW16LXNlY3VyaXR5LXRva2VuIjogIklRb0piM0pwWjJsdVgyVmpFRVVhQ1dWMUxYZGxjM1F0TVNKSE1FVUNJRU5nbmtCUkVsckppZnZseWt4RW9WbWIzK2wwTTI0WjRHa0hUZHZVdmY4dkFpRUFxcms0VXFZUnB2bTY4NFRxMmpSOXQ3QUFNaE0vWHU1ZytEL1MrcTZXT2FVcTNRRUlyZi8vLy8vLy8vLy9BUkFCR2d3MU9URTBNVEF6T0RrM01EY2lERzNVdk90Y051ZGJzQUF1MmlxeEFjeERxNkNqZTRpRzVtdHBoSjlXUU1rbnpydHd0WkNXY0t1TVlrTDJ1bUFrazNiQWJuamV1dC9MVUgwRmxwYU56djdVY2kwdWRoRlc2bFJzMHErbFkyR1hPMnBMZVdJaCtDTk9iZlE1RmlLZEdKNFVNNVNZMFNyOEtrTWJabWJLSEx1eTJqQnpmZ2xrVTNHOFA5UXFLeis3c1Y3Z1VObnZSclRwN2NLZVJVdTR6eUlLbmNIcEp1bnFOQTRqaEpGMm1oSFppeDkwTjVuVXRDTS9tVTZwK0FLbjcwcFRNYzk1RVNWT2xOT2lxYkpiRnpDSXRMYjlCVHJnQWRQaEE1VmdxMmNVWFRJbXdxZW4vZWF6N3BuRU9HU3RkVFdMRWtmOU9UTjlzc2x0OTdtYWt5dVBwdTJRd3A4VmppWWJxdHlmbG1WTXJ2M0MxTHZtYjc2cHJjYXE4dk5adUZLa2ZhV0hRL0UwMzM4ODFTOFBXUDcrcythcm1yQWpGVW41RGl5L2duQnRIV3R3N2NVVTlEbXd5Wlc1ZzJ4cTQzOFhBS2VQeC96aXNZK3pqZjNmWEIyNGptV3dTWVlZRzd5Y3hmWnVDTmNnR2pwcXhXVjI5Vko3UUxtcUV2ZjczZzk4WXNucC9XdGpZaUNRVVFsR1VNeEtESXN6UTVDM0hsNFp1cktvUlRnN0pEbmU1NFlOV0pxMHdSbllsU1NhSlZvOURXODVheCt0In1dfQ==" \
     -F "signature=##########GYiE2mTgM=" \
     -F "file=@intro.mp4" https://s3.eu-west-1.amazonaws.com/videos.serverless.com
```
***7. Add security and authentication***

Installing AWS Boto3
```commandline
$ pip install basicauth
```
We will be setting up the simplest security just to add some basic authentication on our project that we can increase later on.
For that we will be checking if the user and the password is the same just to let access the user. 
```python
@app.authorizer()
def basic_auth(auth_request):
    username, password = decode(auth_request.token)

    if username == password:
        context = {'is_admin': True}        
        return AuthResponse(routes=[AuthRoute('/*', ["GET", "POST"])], principal_id=username, context=context)
    return AuthResponse(routes=[], principal_id=None)
```
Then we can integrate this security just as an extra parameter in the routing anotation:
```python
@app.route('/videos', methods=['GET'], authorizer=basic_auth)
def videos():
```

***8. Add extra routes. We will retrieve and store the information in-memory inside AWS Chalice project.***

We will create a "secure" endpoint to check how many videos has one user uploaded in our platform.

For that we need the following structure:
```python
users_video_dictionary = {
    "eduard@orkei.com": []
}
```
Where we will append all the videos that for which we request a presigned url. Notice that requesting a presigned url doesn't mean that the user will endup using it to upload a video, so this data structure is not 100% consistent with reality. In reality we will be capturing the video upload once is uploaded in S3 so we know for sure that it's there.

We will change the presigned url to add this video information in the in memory data structure:
````python
# GET /presignedurl?mail=eduard@orkei.com
@app.route('/presignedurl', methods=['GET'], cors=cors_config)
def presigned_url():
    mail = app.current_request.query_params.get('mail')

    print("query_param mail: " + mail)

    if len(mail) == 0:
        raise NotFoundError("mail is empty " + mail)

    h = blake2b(digest_size=10)
    byte_mail = bytes(mail, 'utf-8')
    h.update(byte_mail)
    hexmail = h.hexdigest()
    print("hex mail: " + hexmail)

    str_count = ""
    if mail in users_video_dictionary:
        str_count = str(len(users_video_dictionary[mail]))

    new_user_video = hexmail + str_count + '.mp4'
    users_video_dictionary[mail].append(new_user_video)

    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(Bucket="videos.serverless.com",
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
````
Finally we will implement the /videos endpoint with the mail query parameter. 
```python
#/videos?mail=eduard@orkei.com
@app.route('/videos', methods=['GET'], authorizer=basic_auth)
def videos():
    global users_video_dictionary
    app.log.debug("GET Call app.route/register")
    mail = app.current_request.query_params.get('mail')

    if len(mail) == 0:
        raise NotFoundError("mail is empty " + mail)

    if mail in users_video_dictionary:
        return {mail: json.dumps(users_video_dictionary[mail])}
    raise NotFoundError("mail: " + mail + " not found")
```

To test it out just pass the user & password header parameters to the CURL call:

```commandline
$ curl --user "test":"test"  https://####.execute-api.eu-west-1.amazonaws.com/api/videos?mail=eduard@orkei.com

{"eduard@orkei.com":"[]"}
``` 

**Importance to project**

* We are settings the basics for a serverless project where we will allow our users to upload any kind of document into our storage system in a secure way. 
* In a easy way we've just setup AWS Chalice that when deployed has created and configured Amazon API Gateway and our first Serverless Lambda function written in Python. 
* This first Lambda Function handles multiples request, from authentication to generating pre-signed URL to securely upload videos to S3, no matter how big they.
* Also notice that this small architecture can scale horizontally, only limited by the resources that Amazon Web Service can provide (that is quite a lot).     

**Takeaways**
* Hands-on experience with AWS CLI
* Experience creating a project in AWS Chalice
* Hands-on experience with different authentication and security methods in AWS Chalice


**Resources**
* [AWS Chalice Quickstart](https://aws.github.io/chalice/quickstart.html)
* [AWS Chalice Custom Autorizers](https://aws.github.io/chalice/topics/authorizers.html)
* [Boto3 Docs: Generate presigned post](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3.html#S3.Client.generate_presigned_post)
