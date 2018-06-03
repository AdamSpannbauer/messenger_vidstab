"""
Utility functions for working with FB Messenger (sending/receiving messages/challenges)
"""


import os
import json
import dict_utils
import requests


def is_webhook_challenge(event):
    """Check if Lambda event is a FB Messenger webhook challenge

    :param event: AWS Lambda event
    :return: True if event is a FB Messenger webhook challenge; otherwise False
    """
    challenge_keys = ["params", "querystring", "hub.verify_token", "hub.challenge"]
    return dict_utils.keys_exist(event, challenge_keys)


def handle_webhook_challenge(event, verify_token):
    """Handle FB Messenger webhook challenge events

    :param event: AWS Lambda event
    :param verify_token: The token used to verify challenges for the particular FB Messenger app
    :return: The challenge token received in the event
    """
    v_token = str(dict_utils.find_item(event, 'hub.verify_token'))
    challenge = int(dict_utils.find_item(event, 'hub.challenge'))
    if verify_token == v_token:
        return challenge


def is_user_message(event):
    """Check if Lambda event is a FB Messenger message

    :param event: AWS Lambda event
    :return: True if event is a FB Messenger message; otherwise False
    """
    message_keys = ['body-json', 'entry']
    return dict_utils.keys_exist(event, message_keys)


def extract_messaging_event(event):
    """Extract info on user's FB Messenger message from Lambda event

    :param event: AWS Lambda event
    :return: messaging_event dictionary; False if issues retrieving
    """
    try:
        out = event['body-json']['entry'][0]['messaging'][0]
    except KeyError:
        out = False
    except IndexError:
        out = False

    return out


def extract_sender_id(messaging_event):
    """Extract sender id from FB Messenger messaging event

    Function created for consistency with other info extraction methods

    :param messaging_event: messaging_event ( results of extract_messaging_event(event) )
    :return: id of message sender (str)
    """
    return messaging_event['sender']['id']


def extract_video_url(messaging_event):
    """Extract attached video URL from FB Messenger messaging event

    :param messaging_event: messaging_event ( results of extract_messaging_event(event) )
    :return: URL of video attachment received; False if no video attached
    """
    try:
        attachment = messaging_event['message']['attachments'][0]

        if attachment['type'] != 'video':
            rcvd_vid_url = False
        else:
            rcvd_vid_url = attachment['payload']['url']

    except KeyError:
        return False

    return rcvd_vid_url


def send_message(send_id, msg_txt, access_token):
    """Send text to a FB Messenger recipient

    :param send_id: ID of user to send message to
    :param msg_txt: Text contents of message to send
    :param access_token: FB Messenger application's access token
    :return: None
    """
    params = {"access_token": access_token}
    headers = {"Content-Type": "application/json"}
    data = json.dumps({"recipient": {"id": send_id},
                       "message": {"text": msg_txt}})

    r = requests.post("https://graph.facebook.com/v2.6/me/messages", params=params, headers=headers, data=data)

    if r.status_code != 200:
        print(r.status_code)
        print(r.text)


def send_video_attachment(send_id, attach_url, access_token):
    """Send video to a FB Messenger recipient

    :param send_id: ID of user to send message to
    :param attach_url: URL location of video to send
    :param access_token: FB Messenger application's access token
    :return: None
    """
    params = {"access_token": access_token}
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
