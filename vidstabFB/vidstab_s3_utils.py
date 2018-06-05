"""
Utility functions for working with AWS S3 buckets and stabilizing video with vidstab
"""

import tempfile
import uuid
from urllib.request import urlretrieve
import boto3
from botocore.errorfactory import ClientError
import matplotlib
matplotlib.use('Agg')  # set before loading vidstab in lambda function or will have tkinter exception
import vidstab


s3 = boto3.resource('s3')
s3_client = boto3.client('s3')


def s3_obj_exists(bucket, key, verbose=True):
    """Check if key is present in an AWS S3 Bucket

    :param bucket: AWS S3 Bucket in which to search for key
    :param key: key to be searched for in bucket
    :param verbose: Should message concerning object existence be printed?
    :return: True if key is found in bucket; otherwise False
    """
    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        if verbose:
            print('S3 OBJECT EXISTS')
        return True
    except ClientError:
        if verbose:
            print("S3 OBJECT DOESN'T EXIST")
        return False


def stabilize_to_s3(in_url, out_filename, bucket, **kwargs):
    """Wrapper of generic vidstab process that saves to S3 Bucket

    :param in_url: URL path to raw video to be stabilized
    :param out_filename: Filename for stabilized output (will be used as key in S3 Bucket output)
    :param bucket: S3 Bucket to save output to (out_filename will be used as key)
    :param kwargs: keyword arguments to be passed to vidstab.VidStab.stabilize method
    :return: Returns True if no exceptions occur
    """
    with tempfile.TemporaryDirectory() as dirpath:
        # set up file paths for input/output
        in_path = '{}/{}.mp4'.format(dirpath, uuid.uuid4())
        out_path = '{}/{}'.format(dirpath, out_filename)
        # download received video
        urlretrieve(in_url, in_path)
        # init stabilizer
        stabilizer = vidstab.VidStab()
        # stabilize and write
        stabilizer.stabilize(in_path,
                             out_path,
                             **kwargs)
        # upload to s3 bucket
        s3.meta.client.upload_file(out_path,
                                   bucket,
                                   out_filename,
                                   ExtraArgs={'ACL': 'public-read'})

    return True
