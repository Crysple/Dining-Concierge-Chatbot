import json
import boto3
import random


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
    ids = es_search(cuisine)
    rand_id = random.sample(ids, 1)[0]
    record = pullData(rand_id)
    return record
    
    # hardcode
    # d = {
    #     "id": "8ig0yf0003DAp4YOGTlbVg",
    #     "name": "Spicy Village",
    #     "category": "chinese",
    #     "rating": 4.0,
    #     "review_count": 643,
    #     "coordinates": {
    #         "latitude": 40.71695,
    #         "longitude": -73.99327
    #     },
    #     "address": "68 Forsyth St, Ste B, New York, NY 10002",
    #     "phone": "(212) 625-8299",
    #     "zip_code": "10002"

        
    # }
    # return d

def sendSMS(phone_num, message):
    client = boto3.client('sns')
    client.publish(
        PhoneNumber = phone_num,
        # PhoneNumber = '+16462037548',
        Message = message
    )

    
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

        print(message)
        
    except KeyError:
        print('No messages in the queue!')
    
    msg_info = json.loads(message[0]['Body'])
    
    cuisine_type = msg_info['Cuisine']
    date = msg_info['Date']
    reserve_time = msg_info['Time']
    num_ppl = msg_info['NumberOfPeople']
    phone_num = msg_info['PhoneNumber']
    
    recommends = []
    for i in range(1):
        while True:
            print(cuisine_type)
            recommend_info = recommend(cuisine_type)
            if recommend_info not in recommends and recommend_info["address"] != 'None':
                recommends.append(recommend_info)
                break
    
    
    send_message = "Hello! Here are my {} restaurant suggestions for {} people, "\
        "for {} at {}. 1. {}, located at {}, 2. {}, \
        located at {}, 3. {}, located at {}. \
        Enjoy your meal!".format(cuisine_type, num_ppl, date, reserve_time, recommends[0]["name"], recommends[0]["address"], recommends[1]["name"], recommends[1]["address"], recommends[2]["name"], recommends[2]["address"])
    # send_message = "1. {}, located at {}".format(recommends[0]['name'], recommends[0]['address'])

    sendSMS(phone_num, send_message)
    
    
    # delete the message in sqs
    try:
        sqs_client.delete_message(QueueUrl = sqs_url, ReceiptHandle = message[0]['ReceiptHandle'])
    except:
        raise RuntimeError("Failed to delete messages!")
    

