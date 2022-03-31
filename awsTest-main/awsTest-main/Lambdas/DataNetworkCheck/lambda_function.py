#
# DataNetworkCheck - lambda_function.py
#
# Description:- Triggered by call through API Gateway or ALB. 
#               It will read configuration from DynamoDB.
#               Then if a valid service, it will check to see if call is from user on an approved network.
#
# Author: Tim Hessing
# Created: 03-12-2022
# Updated: 03-27-2022
#
import json
import boto3
import ipaddress

#
# Create DynamoDB & SNS Client
#
dynamo_cli = boto3.client('dynamodb')

def lambda_handler(event, context):
    #
    # Make sure Service Table Exists
    #
    try:
        descrTable = dynamo_cli.describe_table(TableName='DNCServiceTable')
        print("Table Exists ", descrTable)
    except:
        print("ERROR: No DNCServiceTable - Nothing to check")
        return
    #
    # See it there are any Services - or nothing to check
    #
    try:
        scanResponse = dynamo_cli.scan(TableName='DNCServiceTable', Select='ALL_ATTRIBUTES')
        print("Scan succeeded ", scanResponse)
    except:
        print("ERROR: DNCServiceTable Scan Failed!!!")
        return

    print("Service Count: ", scanResponse['Count'] )
    if scanResponse['Count'] == 0:  
        print("ERROR: No Services Configured - Nothing to check")
        return
    #
    # Get Configured Services
    #
    services = {}
    badURL = {}
    allowedCIDR = {}
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
 
    #
    # Make sure Main Table Exists
    #
    try:
        descrTable = dynamo_cli.describe_table(TableName='DNCMainTable')
        print("Table Exists ", descrTable)
    except:
        print("ERROR: No DNCMainTable")
        return
    #
    # Now see if anything in it (if not 1st time through - add defaults)
    #
    try:
        scanResponse = dynamo_cli.scan(TableName='DNCMainTable', Select='ALL_ATTRIBUTES')
        print("Scan succeeded ", scanResponse)
    except:
        print("ERROR: DNCMainTable Scan Failed!!!")
        return
    #
    # If count zero then add default item(s) and rescan - or continue
    #
    print("Count: ", scanResponse['Count'] )
    if scanResponse['Count'] == 0:
        item = { "dnc-name": {'S': "mydnc"}, 
                 "default-allowed": {'L': [ {'S': "10.10.10.10/8"}, {'S': "10.10.100.0/32"} ] }, 
                 "service-na-url": {'S': "https://service.data.ohio.gov/sna" }, 
                 "bad-network-url": {'S': "https://service.data.ohio.gov/bnc" } }
                 
        putResponse = dynamo_cli.put_item(TableName='DNCMainTable', Item=item)
        scanResponse = dynamo_cli.scan(TableName='DNCMainTable', Select='ALL_ATTRIBUTES')
        print("Scan succeeded ", scanResponse)
    #
    # Verify 1 item only
    #
    if scanResponse['Count'] != 1:
        print("ERROR: Too many items!!! Count=", scanResponse['Count'])
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
    # Dump event to log for debugging purposes
    #
    #print("Received event: ", json.dumps(event, indent=2))
    #print("Recieved context: ", context)
    #
    # Extract Header/Source IP
    #
    jsevt = json.loads(json.dumps(event))
    #
    # Extract Parameters
    #
    try:
        headerIP = jsevt["multiValueHeaders"]["X-Forwarded-For"][0]
        try:
            service  = jsevt["multiValueQueryStringParameters"]["service"][0]
        except:
            try:
                service  = jsevt["pathParameters"]["service"]
            except:
                #
                # Call improperly configured
                #
                Message = '<h1>The call to this <b style="color:blue">VPN Check Service</b> was <b style="color:red">improperly</b> configured, please contact administrator.</h1>'
                response = {
                    'statusCode': 400,
                    'headers': {'Content-Type': 'text/html'},
                    'body': Message
                }
                print(' Message1: ', Message)
                print('Response1: ', response)
                return response

        print("Servive/IP: ", service, "/", headerIP)
        #
        # Is Service Supported
        #
        if service in services.keys():
            #
            # Destination URL
            print('Service: ', service, ' exists at ', services[service])
            destinationURL = services[service]
            #
            # Bad Network URL
            defaultError = BNEurl
            if badURL[service].lower() != "default":
                defaultError = badURL[service]
            #
            # Net check - Default or not:
            dataNetwork = allowedNet
            if allowedCIDR[service][0].lower() != "default":
                dataNetwork = allowedCIDR[service]
            #
            # Custom IP for service
            for cidr in dataNetwork:
                if ipaddress.ip_address(headerIP) in ipaddress.ip_network(cidr, strict=False):
                    Message = 'On VPN - forwarding to {} at {}'.format(service, destinationURL)
                    response = {
                        'statusCode': 307,
                        'headers': {
                            'Location': destinationURL,
                        }
                    }
                    print(' Message2: ', Message)
                    print('Response2: ', response)
                    return response
            #
            # If we get here - no match to network found
            #
            Message = 'Not on VPN - forwarding to {} to network error page {}'.format(service, defaultError)
            response = {
                'statusCode': 307,
                'headers': {
                    'Location': defaultError,
                }
            }
            print(' Message3: ', Message)
            print('Response3: ', response)
            return response
        else:
            #
            # Service not available
            #
            Message = 'This service {} is not available forwarding to service not available error page {}'.format(service, SNAurl)
            response = {
                'statusCode': 307,
                'headers': {
                    'Location': SNAurl,
                }
            }
            print(' Message4: ', Message)
            print('Response4: ', response)
            return response
    except:
        #
        # Call improperly configured
        #
        Message = '<h1>The call to this <b style="color:blue">Data Network Check Service</b> was <b style="color:red">improperly</b> configured, please contact administrator.</h1>'
        response = {
            'statusCode': 400,
            'headers': {'Content-Type': 'text/html'},
            'body': Message
        }

    print(' Message5: ', Message)
    print('Response5: ', response)    
    return response