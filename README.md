## Securely upload videos to S3 using a serverless architecture

**Objective**

* Using AWS Chalice, we will generate and send to the client a pre-signed URL that can be used to upload a file directly to S3. An S3 bucket and folder structure will be created for uploaded files. It is essential to protect the privacy of our users and data, so we will test security and authentication methods. 
  

**Workflow**

1. Setup and configure AWS CL  
2. Install and setup AWS Chalice
3. Create first project with Chalice
4. Add Python libraries and AWS botocore
5. Create an S3 Bucket
6. Build logic for generating the presigned-url as a URL get request.
7. Add extra routes. We will retrieve and store the information in-memory inside AWS Chalice project.
8. Add security and authentication



**Mileston 1: Submit Your Work**


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

1. Setup and configure AWS CLI
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

2. Install and setup AWS Chalice
```commandline
$ python3 -m pip install chalice
```

3. Create first project with Chalice
```commandline
$ chalice new-project serverlessbackend
$ cd serverlessbackend
```
4. Add Python libraries and AWS botocore
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
Saving pip packages in the requirements
```commandline
 $ pip freeze --local > requirements.txt
```
5. Create an S3 Bucket
6. Build logic for generating the presigned-url as a URL get request.
7. Add extra routes. We will retrieve and store the information in-memory inside AWS Chalice project.
8. Add security and authentication

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
