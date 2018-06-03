# python-lambda-local -f lambda_handler lambda_function.py event.json
import os
import json
import tempfile
import uuid
from urllib.request import urlopen, urlretrieve
import requests
import boto3
from botocore.errorfactory import ClientError
import matplotlib
matplotlib.use('Agg')
import vidstab

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

bucket_name = 'messengervidstabpublic'
last_url = None


def find_item(obj, key):
    if key in obj:
        return obj[key]
    for k, v in obj.items():
        if isinstance(v,dict):
            item = find_item(v, key)
            if item is not None:
                return item


def keys_exist(obj, keys):
    for key in keys:
        if find_item(obj, key) is None:
            return False
    return True


def stabilize_to_s3(in_url, out_filename):
    with tempfile.TemporaryDirectory() as dirpath:
        # set up filepaths for input/output
        in_path = '{}/{}.mp4'.format(dirpath, uuid.uuid4())
        out_path = '{}/{}'.format(dirpath, out_filename)
        # download received video
        urlretrieve(in_url, in_path)
        # init stabilizer
        stabilizer = vidstab.VidStab()
        # stabilize and write
        stabilizer.stabilize(in_path, 
                             out_path, 
                             border_size=100, 
                             output_fourcc='MP4V')
        # upload to s3 bucket
        s3.meta.client.upload_file(out_path,
                                   bucket_name,
                                   out_filename,
                                   ExtraArgs={'ACL': 'public-read'})

    return True

def s3_obj_exists(bucket, key):
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        print('S3 OBJECT EXISTS')
        return True
    except ClientError:
        print("S3 OBJECT DOESN'T EXIST")
        return False

def send_message(send_id, msg_txt):
    params = {"access_token": os.environ['access_token']}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": send_id},
                       "message": {"text": msg_txt}})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

    if r.status_code != 200:
        print(r.status_code)
        print(r.text)


def send_attachment(send_id, attach_url):
    params = {"access_token": os.environ['access_token']}
    headers = {"Content-Type": "application/json"}
    data = json.dumps(
        {"recipient": {
            "id": send_id
        },
            "message": {
                "attachment": {
                    "type": "video",
                    "payload": {
                        "url": attach_url, "is_reusable": True
                    }
                }
            }
        })
    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)
    if r.status_code != 200:
        print(r.status_code)
        print(r.text)


def lambda_handler(event, context):
    global last_url
    print(last_url)
    
    print('\n\nEVENT:')
    print(event)
    print('\n\nCONTEXT:')
    print(context.aws_request_id)

    # handle webhook challenge
    if keys_exist(event, ["params", "querystring", "hub.verify_token", "hub.challenge"]):
        v_token = str(find_item(event, 'hub.verify_token'))
        challenge = int(find_item(event, 'hub.challenge'))
        if os.environ['verify_token'] == v_token:
            return challenge

    # handle messaging events
    if keys_exist(event, ['body-json', 'entry']):
        event_entry0 = event['body-json']['entry'][0]
        if keys_exist(event_entry0, ['messaging']):
            messaging_event = event_entry0['messaging'][0]
            sender_id = messaging_event['sender']['id']
            try:
                attachment = messaging_event['message']['attachments'][0]
                if attachment['type'] == 'video':
                    rcvd_vid_url = attachment['payload']['url']
                    s3_rcvd_vid_id = str(messaging_event['timestamp']) + '_' + sender_id
                    
                    if last_url == rcvd_vid_url or s3_obj_exists('messengervidstaburls', s3_rcvd_vid_id):
                        print('KILLED RETRY')
                        return True
                    else:
                        s3.Object('messengervidstaburls', s3_rcvd_vid_id).put(Body='*')
                        last_url = rcvd_vid_url
                    
                    out_filename = '{}.mp4'.format(uuid.uuid4())
                    s3_result_url = 'https://s3.amazonaws.com/{}/{}'.format(bucket_name, out_filename)
                    
                    stabilize_to_s3(in_url=rcvd_vid_url, out_filename=out_filename)
                    print('attach url')
                    print(s3_result_url)
                    # send_message(send_id=sender_id, msg_txt=s3_result_url)
                    send_attachment(send_id=sender_id,  attach_url=s3_result_url)
                    s3.Object(bucket_name, out_filename).delete()
                else:
                    send_message(send_id=sender_id, msg_txt="Send me a video and I'll do my best to stabilize it & send it back to you!")
            except Exception as e:
                print(e)
                send_message(send_id=sender_id, msg_txt="Send me a video and I'll do my best to stabilize it & send it back to you!")

    return True
