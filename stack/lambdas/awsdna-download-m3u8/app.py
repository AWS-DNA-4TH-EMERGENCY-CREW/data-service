import json
import logging
import os
import subprocess

import boto3
import botocore
import cv2

from video_processor import apply_faces_to_video, integrate_audio

logger = logging.getLogger()
logger.setLevel(logging.INFO)

reko = boto3.client('rekognition')
s3 = boto3.client('s3')

output_bucket = os.environ['OUTPUT_BUCKET']


def lambda_function(event, context):
    logger.log(logging.ERROR, 'Hello SQS and Lambda!')
    logger.log(logging.ERROR, json.dumps(event))

    channel_id = json.loads(event['Records'][0]['body'])['channel_id']
    channel_name = json.loads(event['Records'][0]['body'])['channel_name']

    s3 = boto3.client('s3', region_name='ap-northeast-1')
    obj_list = s3.list_objects_v2(Bucket='ivs-video-archive-us-east-1')
    cl = obj_list['Contents']
    fl = [x['Key'] for x in cl if (
        lambda x:channel_id in x['Key'] and '360p30' in x['Key'] and x['Key'].endswith('.ts'))(x)]

    while 'NextContinuationToken' in obj_list:
        obj_list = s3.list_objects_v2(
            Bucket='ivs-video-archive-us-east-1', ContinuationToken=obj_list['NextContinuationToken'])
        cl = obj_list['Contents']
        fl.extend([x['Key'] for x in cl if (
            lambda x:channel_id in x['Key'] and '360p30' in x['Key'] and x['Key'].endswith('.ts'))(x)])

    logger.log(logging.ERROR, ', '.join(fl))

    for f in fl:
        logger.log(logging.ERROR, 'download key:'+f)
        logger.log(logging.ERROR, 'local path: /tmp/'+f.split('/')[-1])
        s3.download_file('ivs-video-archive-us-east-1',
                         f, '/tmp/'+f.split('/')[-1])

    filePath = "/tmp"
    file_list = sorted(
        [file for file in os.listdir(filePath) if file.endswith(".ts")])

    logger.log(logging.ERROR, 'filelist:'+'\n'.join(file_list))

    with open("/tmp/file_list.txt", "w+") as f:
        for file in file_list:
            f.write("file '{}'\n".format(file))

    os.chdir('/tmp/')
    output = subprocess.check_output(
        ['ffmpeg', '-f', 'concat', '-i', 'file_list.txt', '-c', 'copy', channel_id+'.mp4'])
    # logger.log(logging.ERROR, 'ffmpeg result: '+output)
    logger.log(logging.ERROR, '/tmp/* file list: ' +
               ', '.join(sorted(os.listdir(filePath))))

    # download file locally to /tmp retrieve metadata
    # try:
    #     response = event['response']
    #     # get metadata of file uploaded to Amazon S3
    #     bucket = event['s3_object_bucket']
    #     key = event['s3_object_key']
    #     filename = key.split('/')[-1]
    #     local_filename = '/tmp/{}'.format(filename)
    #     local_filename_output = '/tmp/anonymized-{}'.format(filename)
    # except KeyError:
    #     error_message = 'Lambda invoked without S3 event data. Event needs to reference a S3 bucket and object key.'
    #     logger.log(logging.ERROR, error_message)
    #     # add_failed(bucket, error_message, failed_records, key)

    # try:
    #     s3.download_file(bucket, key, local_filename)
    # except botocore.exceptions.ClientError:
    #     error_message = 'Lambda role does not have permission to call GetObject for the input S3 bucket, or object does not exist.'
    #     logger.log(logging.ERROR, error_message)
    #     # add_failed(bucket, error_message, failed_records, key)
    #     # continue

    #     # get timestamps

    # uploaded modified video to Amazon S3 bucket
    try:
        s3.upload_file('/tmp/'+channel_id+'.mp4', output_bucket,
                       'blur/blured_'+channel_name+'_'+channel_id+'.mp4')
    except boto3.exceptions.S3UploadFailedError:
        error_message = 'Lambda role does not have permission to call PutObject for the output S3 bucket.'
        # add_failed(bucket, error_message, failed_records, key)
        # continue

    return {
        'statusCode': 200,
        'body': json.dumps('Faces in video blurred')
    }
