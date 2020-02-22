#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import boto3
'''
Data format for restaurant json
{
    "id": "p4W_z-zh96LHEAtQ8LRSVQ",
    "name": "Shinagawa",
    "category": "japanese",
    "rating": 4.5,
    "review_count": 112,
    "coordinates": {
        "latitude": 40.74549,
        "longitude": -73.97935
    },
    "address": "157 E 33rd St, New York, NY 10016",
    "phone": "(917) 261-6635",
    "zip_code": "10016",
    "hours": [
        {
            "is_overnight": false,
            "start": "1100",
            "end": "2230",
            "day": 0
        },
        ... to "day": 5
    ]
},
'''
STRING_TYPES = ["id", "name", "category", "address", "phone", "zip_code"]
NUMBERS_TYPES = ["rating", "review_count"]


def removeDataTypes(rstr):
    for key, value in rstr.items():
        assert isinstance(value, dict), "value should be a mapping {dtype: value}"
        dtype, value = [*value.items()][0]
        if dtype == "S":
            rstr[key] = value
        elif dtype == "N":
            rstr[key] = float(value)
        elif dtype == "L":
            rstr[key] = list()
            for v in value:
                removeDataTypes(v)
                rstr[key] += v,
        else:
            raise Exception("Error: unexpected data type {}".format(dtype))

# TODO: modify PutRequest to proper words returned
def unpack(restaurants):
    '''Convert json of restaurants from dynamoDB Insert Request Format back to normal dict'''
    requests = list()
    for rstr in restaurants:
        rstr = rstr["PutRequest"]["Item"]
        rstr = removeDataTypes(rstr)
        requests.append(rstr)

    return {"Restaurants": requests}

def addDataTypes(rstr):
    '''Add dynamoDB types for each attribute'''
    def pack(key, value, Type):
        '''Attribute in dynamoDB: {key: {dataType: value}}'''
        if not value:
            print(key, value, Type)
        return (key, {Type: value})
    #print(rstr)
    nrstr = list()
    for key in STRING_TYPES:
        nrstr += pack(key, rstr[key], "S"),
    for key in NUMBERS_TYPES:
        nrstr += pack(key, str(rstr[key]), "N"),

    for key in ["latitude", "longitude"]:
        nrstr += pack(key, str(rstr["coordinates"][key]), "N"),

    openDays = list()
    for day in rstr["hours"]:
        dayOpenHour = dict([pack(key, str(day[key]), "S") for key in ["day", "start", "end"]])
        openDays += {"M": dayOpenHour},
    nrstr += pack("open_days", openDays, "L"),

    return dict(nrstr)

def pack(restaurants):
    '''Convert json of restaurants to dynamoDB Insert Request Format'''
    requests = list()
    for rstr in restaurants:
        nrstr = addDataTypes(rstr)
        request = {"PutRequest": {"Item": nrstr}}
        requests.append(request)

    return {"Restaurants": requests}

def uploadData(restaurants):
    client = boto3.client('dynamodb')
    response = client.batch_write_item(RequestItems=restaurants)
    print("HTTPStatusCode: {}".format(response['ResponseMetadata']['HTTPStatusCode']))

def pullData(id):
    client = boto3.client('dynamodb')
    response = client.get_item(TableName='Restaurants', Key={'id':{'S': id}})

    return response['Id']

def writeToFile(restaurants, filename):
    with open(filename, "w") as f:
        f.write(json.dumps(restaurants, indent=4))



if __name__ == '__main__':
    restaurants = json.load(open('data.json'))
    res = pack(restaurants[:10])
    
    #writeToFile(res, "formatted_data.json")
    uploadData(res)