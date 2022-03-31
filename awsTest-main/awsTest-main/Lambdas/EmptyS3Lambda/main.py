# EmptyS3Lambda
# Author: Kadambari Athreya & Tim Hessing 
# Nationwide Insurance
# Created: 6/26/2020
# Updated: 3/14/2022
#
# Script to Empty a specified S3 bucket to prep the bucket for deletion
#
import logging
import requests

import json
import boto3

logger = logging.getLogger("empytS3log")
logger.setLevel(logging.DEBUG)

def lambda_handler(event, context):
    logger.info("Starting the Lambda execution ...")   
    logger.debug(f"event: {event}")
    logger.debug(f"context: {context}")

    try:
        bucket_name = event['ResourceProperties']['BucketName']
        logger.debug(f"Bucket being cleanedup is: {bucket_name}")

        if event['RequestType'] == 'Delete':
            s3 = boto3.resource('s3')
            bucket = s3.Bucket(bucket_name)
            logger.debug(f"All object Versions in bucket: {bucket.object_versions.all()}")
            logger.debug("Cleaning up the bucket now....")
            cleanup_response = bucket.object_versions.delete()
            logger.debug(f"Response from bucket cleanup: {cleanup_response}")
            logger.debug(f"Lambda Execution is complete...")         
        else:
            logger.info("Pipeline is not running in delete mode, do nothing")  

        sendResponseCfn(event, context, "SUCCESS")
        logger.info("Lambda execution Complete")   
        
    except Exception as e:
        logger.debug(f"Exception was raised: {e}")
        sendResponseCfn(event, context, "FAILED")

def sendResponseCfn(event, context, responseStatus):
    response_body = {'Status': responseStatus,
                     'Reason': 'Log stream name: ' + context.log_stream_name,
                     'PhysicalResourceId': context.log_stream_name,
                     'StackId': event['StackId'],
                     'RequestId': event['RequestId'],
                     'LogicalResourceId': event['LogicalResourceId'],
                     'Data': json.loads("{}")}

    requests.put(event['ResponseURL'], data=json.dumps(response_body))
