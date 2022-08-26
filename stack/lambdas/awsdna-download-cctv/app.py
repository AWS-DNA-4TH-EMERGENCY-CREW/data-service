import json
import logging
import os
import subprocess

import boto3
import botocore
import datetime
import requests as req

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

output_bucket = os.environ['OUTPUT_BUCKET']


def lambda_function(event, context):

    # m3u8 dynamo에서 읽ㅓㅗ기
    # m3u8 다운로드해서 m3u8 또 다운로드
    # m3u8 에서 *.ts 다운로드

    print(event)
    channelName = event['pathParameters']['channelName']

    guid = 'cctv_'+channelName+'_'+datetime.datetime.now().strftime("%f")
    tmpPrefix = '/tmp/'+guid

    rmOutput = subprocess.check_output(['rm', '-rf', 'tmpPrefix'])
    subprocess.check_output(['mkdir', tmpPrefix])
    # print('rmOutput:' + rmOutput)

    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('channel')
    resp = table.get_item(
        Key={'channel_name': channelName},
    )
    print(resp['Item']['playback_url'])
    url = resp['Item']['playback_url']
    file = req.get(url, allow_redirects=True)
    open(tmpPrefix+'/playlist_'+guid+'.m3u8', 'wb').write(file.content)

    with open(tmpPrefix+'/playlist_'+guid+'.m3u8', "r") as f:
        for line in f:
            pass
        last_line = line

    url2 = last_line.split('\n')[0]
    print('url2:' + url2)
    url3 = '/'.join(url.split('/')[0:-1])+'/'+url2
    print('url3:' + url3)
    file2 = req.get(url3, allow_redirects=True)
    open(tmpPrefix+'/chunklist_'+guid+'.m3u8', 'wb').write(file2.content)

    tsList = []
    with open(tmpPrefix+'/chunklist_'+guid+'.m3u8', "r") as f:
        for line in f:
            if line.endswith('.ts\n'):
                tsList.append(line.split('\n')[0])

    print('ts list:', tsList)

    for file in tsList:
        tsUrl = '/'.join(url.split('/')[0:-1])+'/'+file
        raw = req.get(tsUrl, allow_redirects=True)
        open(tmpPrefix+'/'+guid+file, 'wb').write(raw.content)
        print('tsUrl:', tsUrl)

    # logger.log(logging.ERROR, 'Hello SQS and Lambda!')
    # logger.log(logging.ERROR, json.dumps(event))

    # channel_id = json.loads(event['Records'][0]['body'])['channel_id']
    # channel_name = json.loads(event['Records'][0]['body'])['channel_name']

    # s3 = boto3.client('s3', region_name='ap-northeast-1')
    # obj_list = s3.list_objects_v2(Bucket='ivs-video-archive-us-east-1')
    # cl = obj_list['Contents']
    # fl = [x['Key'] for x in cl if (
    #     lambda x:channel_id in x['Key'] and '360p30' in x['Key'] and x['Key'].endswith('.ts'))(x)]

    # while 'NextContinuationToken' in obj_list:
    #     obj_list = s3.list_objects_v2(
    #         Bucket='ivs-video-archive-us-east-1', ContinuationToken=obj_list['NextContinuationToken'])
    #     cl = obj_list['Contents']
    #     fl.extend([x['Key'] for x in cl if (
    #         lambda x:channel_id in x['Key'] and '360p30' in x['Key'] and x['Key'].endswith('.ts'))(x)])

    # logger.log(logging.ERROR, ', '.join(fl))

    # for f in fl:
    #     logger.log(logging.ERROR, 'download key:'+f)
    #     logger.log(logging.ERROR, 'local path: /tmp/'+f.split('/')[-1])
    #     s3.download_file('ivs-video-archive-us-east-1',
    #                      f, '/tmp/'+f.split('/')[-1])

    filePath = tmpPrefix
    file_list = sorted(
        [file for file in os.listdir(filePath) if file.endswith(".ts")])

    logger.log(logging.ERROR, 'filelist:'+'\n'.join(file_list))

    with open(tmpPrefix+'/file_list_'+guid+'.txt', "w+") as f:
        for file in file_list:
            f.write("file '{}'\n".format(file))

    os.chdir(tmpPrefix+'/')
    output = subprocess.check_output(
        ['ffmpeg', '-f', 'concat', '-i', 'file_list_'+guid+'.txt', '-c', 'copy', 'cctv_'+guid+'.mp4'])
    # logger.log(logging.ERROR, 'ffmpeg result: '+output)
    logger.log(logging.ERROR, tmpPrefix+'/* file list: ' +
               ', '.join(sorted(os.listdir(filePath))))

    # # download file locally to /tmp retrieve metadata
    # # try:
    # #     response = event['response']
    # #     # get metadata of file uploaded to Amazon S3
    # #     bucket = event['s3_object_bucket']
    # #     key = event['s3_object_key']
    # #     filename = key.split('/')[-1]
    # #     local_filename = '/tmp/{}'.format(filename)
    # #     local_filename_output = '/tmp/anonymized-{}'.format(filename)
    # # except KeyError:
    # #     error_message = 'Lambda invoked without S3 event data. Event needs to reference a S3 bucket and object key.'
    # #     logger.log(logging.ERROR, error_message)
    # #     # add_failed(bucket, error_message, failed_records, key)

    # # try:
    # #     s3.download_file(bucket, key, local_filename)
    # # except botocore.exceptions.ClientError:
    # #     error_message = 'Lambda role does not have permission to call GetObject for the input S3 bucket, or object does not exist.'
    # #     logger.log(logging.ERROR, error_message)
    # #     # add_failed(bucket, error_message, failed_records, key)
    # #     # continue

    # #     # get timestamps

    # uploaded modified video to Amazon S3 bucket

    try:
        s3.upload_file(tmpPrefix+'/cctv_'+guid+'.mp4',
                       output_bucket, 'cctv/'+guid+'.mp4')
    except boto3.exceptions.S3UploadFailedError:
        error_message = 'Lambda role does not have permission to call PutObject for the output S3 bucket.'
        # add_failed(bucket, error_message, failed_records, key)
        # continue

    response = {
        'statusCode': 200,
        'body': json.dumps({
            'playback_url': 'https://d3328b7fefvh0o.cloudfront.net/cctv/'+guid+'.mp4'
        }),
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
        }
    }
    print('RESPONSE: ' + response)
    return response
