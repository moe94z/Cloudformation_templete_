#
# UpdateConfig - lambda_function.py
#
# Description:- Triggered by call through ALB from web page (Flask).
#               It will read, write and update a configuration table in DynamoDB.
#
# Author: Tim Hessing
# Created: 03-12-2022
# Updated: 03-27-2022
#
import json
import boto3
import ipaddress

import base64
import re
#
# Create DynamoDB & SNS Client
#
dynamo_cli = boto3.client('dynamodb')

def lambda_handler(event, context):
    #
    # Dump event to log for debugging purposes
    #
    #print("Received event: ", json.dumps(event, indent=2))
    #
    # Get API Command
    try:
        command = event.get('queryStringParameters')['command']
    except:
        command = "null"
    print("Command: ", command.upper())
    #
    # If Read (send back data)
    #
    if command.lower() == "read":
        #
        # Make sure Main & Service Table Exists
        #
        try:
            descrTable = dynamo_cli.describe_table(TableName='DNCMainTable')
            print("Table Exists ", descrTable)
        except:
            print("ERROR: No DNCMainTable")
            return
        #
        try:
            descrTable = dynamo_cli.describe_table(TableName='DNCServiceTable')
            print("Table Exists ", descrTable)
        except:
            print("ERROR: No DNCServiceTable")
            return
        #
        # Scan/Read Main then Services
        try:
            scanResponse = dynamo_cli.scan(TableName='DNCMainTable', Select='ALL_ATTRIBUTES')
            print("Scan succeeded ", scanResponse)
        except:
            print("ERROR: DNCMainTable Scan Failed!!!")
            return
        #
        # Verify 1 and only 1 item 
        #
        if scanResponse['Count'] != 1:
            print("ERROR: Too wrong number of items!!! Count=", scanResponse['Count'])
            return
        #
        # Extract Defaults
        #
        SNAurl = scanResponse['Items'][0]['service-na-url']['S']
        BNEurl = scanResponse['Items'][0]['bad-network-url']['S']
        allowedNet = []
        for da in scanResponse['Items'][0]['default-allowed']['L']:
            allowedNet.append(da['S'])
        #
        # Now the Services table
        try:
            scanResponse = dynamo_cli.scan(TableName='DNCServiceTable', Select='ALL_ATTRIBUTES')
            print("Scan succeeded ", scanResponse)
        except:
            print("ERROR: DNCServiceTable Scan Failed!!!")
            return
        #
        # Get results if any
        #
        services = {}
        badURL = {}
        allowedCIDR = {}
        print("Service Count: ", scanResponse['Count'] )
        if scanResponse['Count'] != 0:
            for item in scanResponse['Items']:
                service     = item['service-name']['S']
                destination = item['destination']['S']
                BNEurl      = item['bad-url']['S']
                allowedNet  = []
                for da in item['allow-net']['L']:
                    allowedNet.append(da['S'])
                print(service, destination, BNEurl, allowedNet)
                services[service]    = destination
                badURL[service]      = BNEurl
                allowedCIDR[service] = allowedNet 
        else:
            print("ERROR: No Services Configured - Nothing to check")
        #
        # pack up the results and send back    
        #
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        # do something        
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

        return
    #
    # If Write (update DB)
    #
    elif command.lower() == "write":
        #
        # Extract Data from body
        #
        input = event.get('body')
        decodedinput = base64.b64decode(input)
        cleaninput   = decodedinput.decode('utf-8')
        input_list   = cleaninput.split('&')
        print(" Input List: ", input_list)
        #
        # Extract Data to update
        SNAurl = ""
        BNEurl = ""
        allowedNet = []
        nwservices = []
        for item in input_list:
            if item[0:12].lower() == "form_submit=":
                form_command = unquote(re.sub('\+', ' ',item[12:].lower()))
            elif item[0:7].lower() == "snaurl=":
                SNAurl = unquote(re.sub('\+', ' ',item[7:].lower()))
            elif item[0:7].lower() == "bneurl=":
                BNEurl = unquote(re.sub('\+', ' ',item[7:].lower()))
            elif item[0:11].lower() == "allowedNet=":
                allowedNet.append(unquote(re.sub('\+', ' ',item[11:].lower())))
            elif item[0:9].lower() == "services=":
                nwservices.append(unquote(re.sub('\+', ' ',item[9:].lower())))

        defallowed = []
        for da in allowedNet:
            mydict = {'S': da}
            defallowed.append(mydict)
        #
        # First the DNCMainTable - dnc-name is the key and should be the same always
        #
        newitem = { "dnc-name": {'S': "mydnc"}, "default-allowed": {'L': defallowed }, "service-na-url": {'S': SNAurl }, "bad-network-url": {'S': BNEurl } }
                 
        putResponse = dynamo_cli.put_item(TableName='DNCMainTable', Item=newitem)
        
        #
        # Now DNCServiceTable (service is the key) - needs o tie to screen inputs for HTML screen
        #
        services = {}
        badURL = {}
        allowedCIDR = {}
        for item in nwservices:
            service     = item['service-name']['S']
            destination = item['destination']['S']
            BNEurl      = item['bad-url']['S']
            allowedNet  = []
            for da in item['allow-net']['L']:
                allowedNet.append(da['S'])
            print(service, destination, BNEurl, allowedNet)
            services[service]    = destination
            badURL[service]      = BNEurl
            allowedCIDR[service] = allowedNet

        #
        # maybe reread and pack up the results and send back    
        #
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        # do something        
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

    #
    # Else bad command
    #
    else:
        print("Invalid Command: ", command.upper())
        
    return
