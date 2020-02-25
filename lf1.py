#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 24 21:35:36 2020

@author: Jin Yan
"""

import math
import dateutil.parser
import datetime
import time
import os
import logging
import boto3
from botocore.exceptions import ClientError
import json


logger = logging.getLogger()
logger.setLevel(logging.DEBUG)


""" --- Helpers to build responses which match the structure of the necessary dialog actions --- """


def get_slots(intent_request):
    return intent_request['currentIntent']['slots']


def elicit_slot(session_attributes, intent_name, slots, slot_to_elicit, message):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'ElicitSlot',
            'intentName': intent_name,
            'slots': slots,
            'slotToElicit': slot_to_elicit,
            'message': message
        }
    }


def close(session_attributes, fulfillment_state, message):
    response = {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Close',
            'fulfillmentState': fulfillment_state,
            'message': message
        }
    }

    return response


def delegate(session_attributes, slots):
    return {
        'sessionAttributes': session_attributes,
        'dialogAction': {
            'type': 'Delegate',
            'slots': slots
        }
    }


# """ --- Helper Functions --- """


def parse_int(n):
    try:
        return int(n)
    except ValueError:
        return float('nan')


def build_validation_result(is_valid, violated_slot, message_content):
    if message_content is None:
        return {
            "isValid": is_valid,
            "violatedSlot": violated_slot,
        }

    return {
        'isValid': is_valid,
        'violatedSlot': violated_slot,
        'message': {'contentType': 'PlainText', 'content': message_content}
    }


def isvalid_date(date):
    try:
        dateutil.parser.parse(date)
        return True
    except ValueError:
        return False
        
def validate_loc(loc):
    return loc.lower() == "manhattan"


def validate_reserve_res(cusine_type, date,reserve_time,loc,num_ppl,phone_num):
    cusine = ['chinese', 'american', 'mexican','korean','japanese','italian','french']
    if cusine_type is not None and cusine_type.lower() not in cusine:
        return build_validation_result(False,
                                      'cusine_type',
                                      'We do not have {}, would you like a different type of cusine?  '
                                      'Our most popular cusine is chinese'.format(cusine_type))

    if date is not None:
        if not isvalid_date(date):
            return build_validation_result(False, 'date', 'I did not understand that, what date would you like to reserve the restaurant?')
        elif datetime.datetime.strptime(date, '%Y-%m-%d').date() <= datetime.date.today():
            return build_validation_result(False, 'date', 'You can reserve the restaurant from tomorrow onwards.  What day would you like to reserve?')

    if reserve_time is not None:
        if len(reserve_time) != 5:
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'reserve_time', None)

        hour, minute = reserve_time.split(':')
        hour = parse_int(hour)
        minute = parse_int(minute)
        if math.isnan(hour) or math.isnan(minute):
            # Not a valid time; use a prompt defined on the build-time model.
            return build_validation_result(False, 'reserve_time', None)

        if hour < 10 or hour > 16:
            # Outside of business hours
            return build_validation_result(False, 'Time', 'Our business hours are from ten a m. to five p m. Can you specify a time during this range?')
    if loc is not None:
        if not validate_loc(loc):
            return build_validation_result(False,'Location','You can only reserve restaurant in Manhattan now')

    return build_validation_result(True, None, None)


# """ --- Functions that control the bot's behavior --- """


def reserve_res(intent_request):
    """
    Performs dialog management and fulfillment for ordering flowers.
    Beyond fulfillment, the implementation of this intent demonstrates the use of the elicitSlot dialog action
    in slot validation and re-prompting.
    """

    cusine_type = get_slots(intent_request)["Cuisine"]
    date = get_slots(intent_request)["Date"]
    reserve_time = get_slots(intent_request)["Time"]
    #source = intent_request['invocationSource']
    loc = get_slots(intent_request)["Location"]
    num_ppl = get_slots(intent_request)["NumberOfPeople"]
    phone_num = get_slots(intent_request)["PhoneNumber"]
    source = intent_request['invocationSource']
    if source == 'DialogCodeHook':
        # Perform basic validation on the supplied input slots.
        # Use the elicitSlot dialog action to re-prompt for the first violation detected.
        slots = get_slots(intent_request)

        validation_result = validate_reserve_res(cusine_type, date,reserve_time,loc,num_ppl,phone_num)
        if not validation_result['isValid']:
            slots[validation_result['violatedSlot']] = None
            return elicit_slot(intent_request['sessionAttributes'],
                              intent_request['currentIntent']['name'],
                              slots,
                              validation_result['violatedSlot'],
                              validation_result['message'])

        # Pass the price of the flowers back through session attributes to be used in various prompts defined
        # on the bot model.
        output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
        #if flower_type is not None:
            #output_session_attributes['Price'] = len(flower_type) * 5  # Elegant pricing model

        return delegate(output_session_attributes, get_slots(intent_request))

    # Order the flowers, and rely on the goodbye message of the bot to define the message to the end user.
    # In a real bot, this would likely involve a call to a backend service.
    
    sqs_client = boto3.client('sqs')
    sqs_url = 'https://sqs.us-east-1.amazonaws.com/415865090458/restaurant'
    # original  = res_info["PhoneNumber"]
    # res_info["PhoneNumber"] = "+1" + original
    msg_info = {"Cuisine": cusine_type, "Date": date, "Time": reserve_time, "Location":loc,"NumberOfPeople":num_ppl,"PhoneNumber":phone_num}
    print("message to sent is {}".format(msg_info))
   # print(res_info)
    try:
        response = sqs_client.send_message(QueueUrl=sqs_url,
                                      MessageBody=json.dumps(msg_info))
        print(response)
    except ClientError as e:
        logging.error(e)
        return None
    return close(intent_request['sessionAttributes'],
                 'Fulfilled',
                 {'contentType': 'PlainText',
                  'content': "You’re all set. Expect my suggestions shortly! Have a good day."})


# """ --- Intents --- """


def dispatch(intent_request):
    """
    Called when the user specifies an intent for this bot.
    """

    logger.debug('dispatch userId={}, intentName={}'.format(intent_request['userId'], intent_request['currentIntent']['name']))

    intent_name = intent_request['currentIntent']['name']

    # Dispatch to your bot's intent handlers
    if intent_name == 'DiningSuggestionsIntent':
        return reserve_res(intent_request)
    elif intent_name == 'ThankYouIntent':
        return thankyou(intent_request)
    elif intent_name == 'GreetingIntent':
        return greeting(intent_request)

    raise Exception('Intent with name ' + intent_name + ' not supported')
    
def thankyou(intent_request):
    output_session_attributes = intent_request['sessionAttributes'] if intent_request['sessionAttributes'] is not None else {}
    return close(
        output_session_attributes,
        'Fulfilled',
        {
            'contentType': 'PlainText',
            'content': "You are welcome."
        }
    )
    
def greeting(intent_request):
    response = {
        "dialogAction": {
            "type": "Close",
            "fulfillmentState": "Fulfilled",
            "message": {
                "contentType": "PlainText",
                "content": "Hi there, how can I help?"
            }
        }
    }
    return response
    


# """ --- Main handler --- """


def lambda_handler(event, context):
    """
    Route the incoming request based on intent.
    The JSON body of the request is provided in the event slot.
    """
    # By default, treat the user request as coming from the America/New_York time zone.
    print(event)
    print(context)
    os.environ['TZ'] = 'America/New_York'
    time.tzset()
    logger.debug('event.bot.name={}'.format(event['bot']['name']))

    return dispatch(event)
   
 