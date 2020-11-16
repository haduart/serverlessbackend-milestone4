from botocore.exceptions import ClientError
from chalice import Chalice, CORSConfig, NotFoundError, BadRequestError, Response, AuthResponse, AuthRoute, \
    CognitoUserPoolAuthorizer
from basicauth import decode
import logging
import boto3
from hashlib import blake2b
import json

app = Chalice(app_name='serverlessbackend')

app.log.setLevel(logging.DEBUG)

cors_config = CORSConfig(allow_origin="*")

users_dictionary = {
    "eduard@orkei.com": {"password": "liveproject", "videos": []}
}


@app.route('/')
def index():
    return {'hello': 'world'}


@app.authorizer()
def basic_auth(auth_request):
    mail, password = decode(auth_request.token)
    app.log.debug("basic_auth " + mail + ", " + password)
    app.log.debug("basic_auth jsondumps: " + json.dumps(users_dictionary))

    if mail in users_dictionary:
        app.log.debug("basic_auth : mail in users_dictionary")

    if mail in users_dictionary and users_dictionary[mail]["password"] == password:
        app.log.debug("basic_auth : mail in users_dictionary and users_dictionary[mail][password] == password")
        context = {'is_admin': True}
        return AuthResponse(routes=[AuthRoute('/*', ["GET", "POST"])], principal_id=mail, context=context)
    return AuthResponse(routes=[], principal_id=None)


@app.route('/hello', methods=['GET'], authorizer=basic_auth)
def hi():
    context = app.current_request.context['authorizer']
    return {'hello': context["principalId"], 'context': context}


@app.route('/register', methods=['POST'], cors=cors_config)
def register():
    global users_dictionary
    app.log.debug("GET Call app.route/register")
    json_body = app.current_request.json_body
    mail = json_body["mail"]
    password = json_body["password"]

    users_dictionary[mail] = {"password": password, "videos": []}
    return {"success": True, "users_dictionary": json.dumps(users_dictionary)}


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

    s3_client = boto3.client('s3')
    try:
        response = s3_client.generate_presigned_post(Bucket="videos.oico.com",
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

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
