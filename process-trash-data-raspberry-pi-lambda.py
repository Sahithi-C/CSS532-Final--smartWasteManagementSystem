import json
import boto3
import os
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sns_client = boto3.client('sns')
timestream_client = boto3.client('timestream-write')

MAX_BIN_HEIGHT = 29.0

def convert_to_pst(unix_timestamp):
    utc_time = datetime.fromtimestamp(unix_timestamp, tz=timezone.utc)
    pst_offset = timedelta(hours=-8) 
    pst_time = utc_time + pst_offset
    return int(pst_time.timestamp() * 1000) 

def calculate_percentages(distance_cm):

    distance = max(0, min(distance_cm, MAX_BIN_HEIGHT))
    
    remaining_percentage = (distance / MAX_BIN_HEIGHT) * 100
    filled_percentage = 100 - remaining_percentage
    
    return remaining_percentage, filled_percentage

def get_severity_level(remaining_percentage):

    if remaining_percentage <= 10:
        return "SEV1 - CRITICAL"
    elif remaining_percentage <= 20:
        return "SEV2 - HIGH"
    elif remaining_percentage <= 30:
        return "SEV3 - MEDIUM"
    else:
        return None

def send_sns_alert(sns_topic_arn, bin_id, distance_cm, remaining_percentage, filled_percentage, severity):

    message = (
        f"🚨 Bin Capacity Alert 🚨\n"
        f"Bin ID: {bin_id}\n"
        f"Current Distance: {distance_cm:.2f} cm\n"
        f"Remaining Capacity: {remaining_percentage:.2f}%\n"
        f"Filled Capacity: {filled_percentage:.2f}%\n"
        f"Severity: {severity}"
    )
    
    logger.info(f"Sending SNS alert: {message}")
    
    sns_client.publish(
        TopicArn=sns_topic_arn,
        Message=message,
        Subject=f"Bin {bin_id} - {severity} Capacity Alert"
    )

def lambda_handler(event, context):
    logger.info(f"Received event: {event}")
    
    try:
        if "distance_cm" not in event or "timestamp" not in event or "bin_id" not in event:
            logger.error("Event is missing one or more required keys: 'distance_cm', 'timestamp', 'bin_id'.")
            return {
                'statusCode': 400,
                'body': json.dumps("Invalid event format. Required keys: 'distance_cm', 'timestamp', 'bin_id'.")
            }

        distance_cm = event["distance_cm"]
        unix_timestamp = event["timestamp"]
        bin_id = event["bin_id"]

        if not isinstance(distance_cm, (float, int)) or not isinstance(unix_timestamp, (float, int)) or not isinstance(bin_id, str):
            logger.error("Invalid data types in event.")
            return {
                'statusCode': 400,
                'body': json.dumps("Invalid data types for keys.")
            }

        pst_timestamp = convert_to_pst(unix_timestamp)
        formatted_distance = f"{distance_cm:.2f}"
        
        remaining_percentage, filled_percentage = calculate_percentages(distance_cm)
        
        logger.info(f"Formatted distance: {formatted_distance} cm, Remaining %: {remaining_percentage:.2f}%, Filled %: {filled_percentage:.2f}%, Bin ID: {bin_id}")
        
        sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
        timestream_db = os.environ.get('TIMESTREAM_DATABASE')
        timestream_table = os.environ.get('TIMESTREAM_TABLE')
        
        if not sns_topic_arn:
            logger.error("SNS_TOPIC_ARN environment variable is not set.")
            return {
                'statusCode': 500,
                'body': json.dumps('SNS_TOPIC_ARN environment variable is not set.')
            }
        
        if not timestream_db or not timestream_table:
            logger.error("Timestream database or table environment variables are not set.")
            return {
                'statusCode': 500,
                'body': json.dumps('Timestream database or table environment variables are not set.')
            }
        
        severity = get_severity_level(remaining_percentage)
        if severity:
            send_sns_alert(sns_topic_arn, bin_id, distance_cm, remaining_percentage, filled_percentage, severity)
        
        logger.info("Writing to Timestream...")
        timestream_client.write_records(
            DatabaseName=timestream_db,
            TableName=timestream_table,
            Records=[
                {
                    'Dimensions': [
                        {'Name': 'Source', 'Value': 'Raspberry-Pi'},
                        {'Name': 'BinID', 'Value': bin_id},
                        {'Name': 'Severity', 'Value': severity or 'NORMAL'},
                        {'Name': 'RemainingPercentage', 'Value': f"{remaining_percentage:.2f}"},
                        {'Name': 'FilledPercentage', 'Value': f"{filled_percentage:.2f}"},
                        {'Name': 'OriginalDistance', 'Value': formatted_distance}
                    ],
                    'MeasureName': 'remaining_capacity_percentage',
                    'MeasureValue': f"{remaining_percentage:.2f}",
                    'MeasureValueType': 'DOUBLE',
                    'Time': str(pst_timestamp),
                    'TimeUnit': 'MILLISECONDS'
                }
            ]
        )
        logger.info("Data written to Timestream successfully.")
        
        return {
            'statusCode': 200,
            'body': json.dumps(f"Distance {formatted_distance} cm from bin {bin_id} processed. Remaining: {remaining_percentage:.2f}%, Filled: {filled_percentage:.2f}%")
        }
    except Exception as e:
        logger.error(f"Error encountered: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }