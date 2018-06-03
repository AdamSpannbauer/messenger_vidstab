import os
import uuid
import messenger_utils
import vidstab_s3_utils
import boto3

s3 = boto3.resource('s3')

# Bucket to save stabilized videos to. Bucket is public so FB Messenger can access contents.
bucket_name = 'messengervidstabpublic'
# Bucket to log messaging event info to. This is used to prevent same event triggering function multiple times
log_bucket_name = 'messengervidstaburls'

# Text to send to user if no video received to stabilize
default_response = "Send me a video and I'll do my best to stabilize it & send it back to you!"


def is_lambda_retrigger(messaging_event, log_bucket):
    """Util to prevent same event triggering Lambda function multiple times

    :param messaging_event: FB messenger event ( use messenger_utils.extract_messaging_event(event) )
    :param log_bucket: Bucket to log messaging event info to
    :return: True if messaging_event is already logged in log_bucket; otherwise False
    """
    log_id = str(messaging_event['timestamp']) + '_' + messenger_utils.extract_sender_id(messaging_event)
    if vidstab_s3_utils.s3_obj_exists('messengervidstaburls', log_id):
        return True
    else:
        s3.Object(log_bucket, log_id).put(Body='*')
        return False


def lambda_handler(event, context):
    """Lambda function to receive/stabilize videos received through FB Messenger

    :param event: AWS Lambda event
    :param context: AWS Lambda context
    :return: If event is a FB webhook challenge then the received challenge is returned;
             otherwise a string noting the status of the process is returned
    """

    print('\n\nEVENT:')
    print(event)

    # check if event is webhook challenge and handle if True
    if messenger_utils.is_webhook_challenge(event):
        print('RECEIVED WEBHOOK CHALLENGE')
        return messenger_utils.handle_webhook_challenge(event, os.environ['verify_token'])

    # check if event is user messenger event if true:
    # run video stabilization process or respond with default message(s)
    if messenger_utils.is_user_message(event):
        print('RECEIVED MESSAGE')
        # extract info of note from event
        messaging_event = messenger_utils.extract_messaging_event(event)
        if not messaging_event:
            return 'UNEXPECTED EVENT'

        sender_id = messenger_utils.extract_sender_id(messaging_event)
        rcvd_vid_url = messenger_utils.extract_video_url(messaging_event)

        # respond with default message if no video received
        if not rcvd_vid_url:
            messenger_utils.send_message(send_id=sender_id,
                                         msg_txt=default_response,
                                         access_token=os.environ['access_token'])

        # stop processing if this is a retry of an already processed/in process event
        elif is_lambda_retrigger(messaging_event, log_bucket_name):
            return 'KILLED RETRY'

        # create key to save stabilized video to in S3 Bucket
        out_filename = '{}.mp4'.format(uuid.uuid4())
        s3_result_url = 'https://s3.amazonaws.com/{}/{}'.format(bucket_name, out_filename)

        # perform vidstab process and save to S3 bucket
        vidstab_s3_utils.stabilize_to_s3(in_url=rcvd_vid_url,
                                         out_filename=out_filename,
                                         bucket=bucket_name)

        # send stabilized video back to user
        messenger_utils.send_video_attachment(send_id=sender_id,
                                              attach_url=s3_result_url,
                                              access_token=os.environ['access_token'])

        # delete stabilized video from S3 Bucket
        s3.Object(bucket_name, out_filename).delete()

    return 'EXECUTED WITHOUT ERROR'
