import json
import boto3
import random
from utils import get_restaurant_from_dynamoDB, get_restaurants_from_es


'''
1. pulls a message from the SQS queue (Q1), 
2. gets a random restaurant recommendation for the cuisine collected through conversation from ElasticSearch and DynamoDB, 
3. formats them and 4. sends them over text message to the phone number included in the SQS message, using SNS
'''

def recommend(cuisine):
    '''
    input: cusine_type
    output: data record pulled from dynamodb in dictionary format
    '''
    # elastic search
    ids = get_restaurants_from_es(cuisine)

    rand_ids = random.sample(ids, 3)
    records = []
    for id in rand_ids:
        records.append(get_restaurant_from_dynamoDB(id))
    return records


def sendSMS(phone_num, message):
    client = boto3.client('sns')
    response = client.publish(
        PhoneNumber = phone_num,
        Message = message
    )
    # print(response)

    
def lambda_handler(event, context):
    # TODO implement
    sqs_client = boto3.client('sqs')
    sqs_url = 'https://sqs.us-east-1.amazonaws.com/415865090458/restaurant'
    # sqs_url = 'https://sqs.us-east-1.amazonaws.com/415865090458/test1'
    resp = sqs_client.receive_message(QueueUrl = sqs_url, AttributeNames = ['All'])
    
    try:
        message = resp['Messages']
        # [{'MessageId': ..., 'ReceiptHandle': 'xx', 'MD5OfBody': 'xx', 
        # 'Body': '{"Cuisine": "french", "Date": "tomorrow", "Time": "7:00 pm", "Location": "manhattan", "NumberOfPeople": 2, "PhoneNumber": "6462032414"}'}}]

        # print(message)
        
    except KeyError:
        print('No messages in the queue!')
    
    msg_info = json.loads(message[0]['Body'])
    
    cuisine_type = msg_info['Cuisine']
    date = msg_info['Date']
    reserve_time = msg_info['Time']
    num_ppl = msg_info['NumberOfPeople']
    phone_num = msg_info['PhoneNumber']

    recommends = recommend(cuisine_type)

    send_message = "Hello! Here are my {} restaurant suggestions for {} people, "\
        "for {} at {}. 1. {}, located at {}, 2. {}, \
        located at {}, 3. {}, located at {}. \
        Enjoy your meal!".format(cuisine_type, num_ppl, date, reserve_time, recommends[0]["name"], recommends[0]["address"], recommends[1]["name"], recommends[1]["address"], recommends[2]["name"], recommends[2]["address"])

    print(send_message)
    sendSMS(phone_num, send_message)
    

    # delete the message in sqs
    try:
        sqs_client.delete_message(QueueUrl = sqs_url, ReceiptHandle = message[0]['ReceiptHandle'])

    except:
        raise RuntimeError("Failed to delete messages!")
    


