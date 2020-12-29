from botocore.exceptions import ClientError
from chalice import Chalice, CORSConfig, NotFoundError, BadRequestError, Response, AuthResponse, AuthRoute, \
    CognitoUserPoolAuthorizer
from basicauth import decode
import logging
import boto3
from hashlib import blake2b
import json
import os
from boto3.dynamodb.conditions import Key
import random

app = Chalice(app_name='serverlessbackend')

_S3_CLIENT = None
_DYNAMODB_CLIENT = None
_DYNAMODB_TABLE = None
_DYNAMODB_METADATA_TABLE = None
_ELASTIC_TRANSCODER_CLIENT = None
_TRANSCRIBE_CLIENT = None
_SUPPORTED_VIDEO_EXTENSIONS = (
    '.mp4'
)
_SUPPORTED_AUDIO_EXTENSIONS = (
    '.mp3'
)
_SUPPORTED_TEXT_EXTENSIONS = (
    '.json'
)

app.log.setLevel(logging.DEBUG)

RESPONSES_TABLE_NAME = os.getenv('RESPONSES_TABLE_NAME', 'responses')
METADATA_TABLE_NAME = os.getenv('METADATA_TABLE_NAME', 'metadata')
MEDIA_BUCKET_NAME = os.getenv('MEDIA_BUCKET_NAME', 'videos.oico.com')
AUDIO_MEDIA_BUCKET_NAME = os.getenv('AUDIO_MEDIA_BUCKET_NAME', 'outputvideos.oico.com')
PIPELINE_NAME = os.getenv('PIPELINE_NAME', '1607332673743-ta1eh3')

cors_config = CORSConfig(allow_origin="*")


def get_transcribe_client():
    global _TRANSCRIBE_CLIENT
    if _TRANSCRIBE_CLIENT is None:
        _TRANSCRIBE_CLIENT = boto3.client('transcribe')
    return _TRANSCRIBE_CLIENT


def get_elastictranscoder_client():
    global _ELASTIC_TRANSCODER_CLIENT
    if _ELASTIC_TRANSCODER_CLIENT is None:
        _ELASTIC_TRANSCODER_CLIENT = boto3.client('elastictranscoder')
    return _ELASTIC_TRANSCODER_CLIENT


def get_dynamodb_table():
    global _DYNAMODB_TABLE
    global _DYNAMODB_CLIENT
    if _DYNAMODB_TABLE is None:
        if _DYNAMODB_CLIENT is None:
            _DYNAMODB_CLIENT = boto3.resource('dynamodb')
        _DYNAMODB_TABLE = _DYNAMODB_CLIENT.Table(RESPONSES_TABLE_NAME)
    return _DYNAMODB_TABLE


def get_dynamodb_metadata_table():
    global _DYNAMODB_METADATA_TABLE
    global _DYNAMODB_CLIENT
    if _DYNAMODB_METADATA_TABLE is None:
        if _DYNAMODB_CLIENT is None:
            _DYNAMODB_CLIENT = boto3.resource('dynamodb')
        _DYNAMODB_METADATA_TABLE = _DYNAMODB_CLIENT.Table(METADATA_TABLE_NAME)
    return _DYNAMODB_METADATA_TABLE


def get_s3_client():
    global _S3_CLIENT
    if _S3_CLIENT is None:
        _S3_CLIENT = boto3.client('s3')
    return _S3_CLIENT


@app.route('/')
def index():
    s3_clientobj = get_s3_client().get_object(Bucket='outputvideos.oico.com',
                                              Key='output/transcribe/videoask.json')
    s3_clientdata = s3_clientobj['Body'].read().decode('utf-8')

    print("printing s3_clientdata")
    print(s3_clientdata)

    s3clientlist = json.loads(s3_clientdata)
    print("json loaded data")
    print("status: " + s3clientlist['status'])
    transcript = s3clientlist['results']['transcripts'][0]['transcript']
    print("transcript: " + transcript)
    return {'transcript': transcript}


@app.authorizer()
def basic_auth(auth_request):
    username, password = decode(auth_request.token)

    if username == password:
        context = {'is_admin': True}
        # return AuthResponse(routes=['/*'], principal_id=username)
        return AuthResponse(routes=[AuthRoute('/*', ["GET", "POST"])], principal_id=username, context=context)
    return AuthResponse(routes=[], principal_id=None)


@app.route('/hello', methods=['GET'], authorizer=basic_auth)
def hi():
    context = app.current_request.context['authorizer']
    return {'hello': context["principalId"], 'context': context}


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


@app.on_s3_event(bucket=MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_object_created(event):
    print("handle_object_created: " + event.key)
    if _is_video(event.key):
        print("Correct video uploaded: " + event.key)
        transcoder_video(event.key)


@app.on_s3_event(bucket=AUDIO_MEDIA_BUCKET_NAME,
                 events=['s3:ObjectCreated:*'])
def handle_audio_created(event):
    print("handle_audio_created: " + event.key)
    if _is_audio(event.key):
        print("Correct Audio generated: " + event.key)
        random_name = str(random.randint(10000, 99999))
        job_name = "JobName" + random_name
        job_uri = "s3://" + AUDIO_MEDIA_BUCKET_NAME + "/" + event.key
        get_transcribe_client().start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaSampleRateHertz=44100,
            MediaFormat='mp4',
            LanguageCode='en-US',
            OutputBucketName=AUDIO_MEDIA_BUCKET_NAME,
            OutputKey=event.key.replace("mp3", "json").replace("audio", "transcribe"),
        )

        status = get_transcribe_client().get_transcription_job(TranscriptionJobName=job_name)
        print(status)
        return {'transcribe': job_name}
    elif _is_text(event.key):
        print("Correct JSON generated: " + event.key)
        s3_clientobj = get_s3_client().get_object(Bucket=event.bucket,
                                                  Key=event.key)
        s3_clientdata = s3_clientobj['Body'].read().decode('utf-8')

        print("printing s3_clientdata")
        print(s3_clientdata)

        s3clientlist = json.loads(s3_clientdata)
        print("json loaded data")
        print("status: " + s3clientlist['status'])
        transcript = s3clientlist['results']['transcripts'][0]['transcript']
        print("transcript: " + transcript)

        try:
            get_dynamodb_metadata_table().put_item(Item={
                "JsonFile": event.key,
                "transcript": transcript
            })
        except Exception as e:
            print(e)
            raise NotFoundError("Error adding an element on dynamodb")


def create_elastic_transcoder_job(pipeline_id, input_file,
                                  outputs, output_file_prefix):
    """Create an Elastic Transcoder job

    :param pipeline_id: string; ID of an existing Elastic Transcoder pipeline
    :param input_file: string; Name of existing object in pipeline's S3 input bucket
    :param outputs: list of dictionaries; Parameters defining each output file
    :param output_file_prefix: string; Prefix for each output file name
    :return Dictionary containing information about the job
            If job could not be created, returns None
    """

    try:
        response = get_elastictranscoder_client().create_job(PipelineId=pipeline_id,
                                                             Input={'Key': input_file},
                                                             Outputs=outputs,
                                                             OutputKeyPrefix=output_file_prefix)
    except ClientError as e:
        print(f'ERROR: {e}')
        return None
    return response['Job']


def transcoder_video(input_file):
    # Job configuration settings. Set these values before running the script.
    pipeline_id = PIPELINE_NAME  # ID of an existing Elastic Transcoder pipeline
    output_file = input_file  # Desired root name of the transcoded output files

    # Other job configuration settings. Optionally change as desired.
    output_file_prefix = 'output/'  # Prefix for all output files

    system_preset_web_preset_id = '1351620000001-100070' #mp4
    system_preset_iPhone4S = '1351620000001-100020' #mp4
    system_preset_Audio_MP3_320k = '1351620000001-100110' #mp3
    system_preset_Gif_Animated = '1351620000001-100200' #gif

    system_preset_webm_720p_preset_id = '1351620000001-100240'
    system_preset_webm_VP9_720p_preset_id = '1351620000001-100250'
    system_preset_webm_VP9_360p_preset_id = '1351620000001-100260'

    # Define the various outputs
    outputs = [
        {
            'Key': 'web/' + output_file,
            'PresetId': system_preset_web_preset_id
        },
        {
            'Key': 'phone/' + output_file,
            'PresetId': system_preset_iPhone4S
        },
        {
            'Key': 'audio/' + output_file.replace("mp4", "") + "mp3",
            'PresetId': system_preset_Audio_MP3_320k
        },
        {
            'Key': 'gif/' + output_file.replace("mp4", "") + "gif",
            'PresetId': system_preset_Gif_Animated
        }
    ]

    # Create a job in Elastic Transcoder
    job_info = create_elastic_transcoder_job(pipeline_id,
                                             input_file,
                                             outputs, output_file_prefix)
    if job_info is None:
        print("job_info is None!!!!")

    # Output job ID and exit. Do not wait for the job to finish.
    print(f'Created Amazon Elastic Transcoder job {job_info["Id"]}')


# @app.on_sns_message(topic=os.environ['VIDEO_TOPIC_NAME'])
# def add_video_file(event):
#    message = json.loads(event.message)
#    labels = get_rekognition_client().get_video_job_labels(message['JobId'])
#    get_media_db().add_media_file(
#        name=message['Video']['S3ObjectName'],
#        media_type=db.VIDEO_TYPE,
#        labels=labels)

def _is_audio(key):
    return key.endswith(_SUPPORTED_AUDIO_EXTENSIONS)


def _is_text(key):
    return key.endswith(_SUPPORTED_TEXT_EXTENSIONS)


def _is_video(key):
    return key.endswith(_SUPPORTED_VIDEO_EXTENSIONS)
