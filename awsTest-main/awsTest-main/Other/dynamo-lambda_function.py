#
# safeTranslator - lambda_function.py
#
# Description:- Triggered by user adding location in SAFE UI.
#               This will take that location (Postal Code) and convert into geographic coordinates needed
#               for overall solution. It then finds finds its geographic center, uses this to find county code (weather.gov)
#               Then save those coordinates (zone, postal code, etc..), where the key is the county zone.
#               Note: County Zones may have multiple postal codes and multiple users
#
# Author: Tim Hessing
# Created: 03-12-2020
# Updated: 03-21-2020
#
import json
import boto3
import time
import re
import urllib.request
#
# Define APIs
#
postcodeAPI = 'https://maps.googleapis.com/maps/api/geocode/json?key=AIzaSyDEbY53x-JF2q4tAfgF25KmcLsr2UCwimw&components=postal_code:'
pointAPI    = 'https://api.weather.gov/zones?point='
#
# Create DynamoDB Resource and Client
#
dynamo_cli = boto3.client('dynamodb')

def lambda_handler(event, context):
    #
    # Dump event to log for debugging purposes
    #
    print("Received event: " + json.dumps(event, indent=2))
    
    #
    # Extract Command (add or remove), User, and Postal Code
    #
    command     = event.get('queryStringParameters')['command']
    user        = event.get("queryStringParameters")['user']
    postal_code = event.get("queryStringParameters")['zip']
    print("Command: ", command, " zone information for Postal Code: ", postal_code, " related to User: ", user)

    #
    # Check for 5 digit US only zip (or extract from 5 digit - 4 digit zip first 5)
    #
    if re.match('\d{5}$', postal_code) or re.match('^(\d{5})([- ])?(\d{4})?$', postal_code):
        print("GOOD Zip: ", postal_code, postal_code[0:5])
        postal_code = postal_code[0:5]
    else:
        #
        # Create Response
        #
        response = 'Bad zip {} must be 5 digit of 5-4 digit US only zip.'.format(postal_code)
        #
        # Return Response
        #
        result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
        return result
    #
    # Get zone Table and extract all zones (items)
    #
    zone = []
    try:
        scanResponse = dynamo_cli.scan(TableName='SAFE-zones',
                                        IndexName='zone-index',
                                        ProjectionExpression='#myz, #pub, fire, postal_code, subscribers, #nm, #st', 
                                        ExpressionAttributeNames={'#myz': 'zone', '#pub': 'public', '#nm': 'name', '#st': 'state'})
        print("SAFE-zone scan successful!!! ")
        #
        # Get Existing Zones
        #
        zones = scanResponse
        for azs in zones['Items']:
            zone.append(azs)
        print("Zone Items: ", zone)

    except:
        print("Scan Failed!!!")
        if command == 'remove':
            #
            # Create Response
            #
            response = 'Scan Failed - No Alerts Zones Found.'
            #
            # Return Response
            #
            result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
            return result
        else:
            #
            # Create the Table
            #
            dynamo_cli.create_table(TableName='SAFE-zones',
                                    KeySchema=[ {'AttributeName': 'zone', 'KeyType': 'HASH'}, ],
                                    AttributeDefinitions=[{'AttributeName': 'zone', 'AttributeType': 'S'}],
                                    ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5},
                                    GlobalSecondaryIndexes=[
                                        { 'IndexName': 'zone-index',
                                        'KeySchema': [{'AttributeName': 'zone', 'KeyType': 'HASH'}],
                                        'Projection': {'ProjectionType': 'ALL'},
                                        'ProvisionedThroughput': {'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}}],
                                    Tags=[
                                        {'Key': 'ResourceName', 'Value': 'SAFE-zones Table'},
                                        {'Key': 'ResourceOwner', 'Value': 'hessit1'},
                                        {'Key': 'DisbursementCode', 'Value': '301962001'},
                                        {'Key': 'DataClassification', 'Value': 'Internal_Use_Only'},
                                        {'Key': 'APRMID', 'Value': '9999'}
                                    ],
                                )
            time.sleep(15)
    #
    # Table now exists and zone may or may not contain the zone(s). 
    #
    # Remove User from Zone
    #
    if command == 'remove':
        #
        # If there are zones
        #
        if zone:
            #
            # Find zone item with this user
            #
            for item in zone:
                #
                # Does zone item match Postal Code?
                #
                for pc in item['postal_code']['L']:
                    if pc['S'] == postal_code:
                        #
                        # See if User is in this zone
                        #
                        try:
                            #
                            # User exist if this doesn't cause an exception
                            #
                            userin = item['subscribers']['L'].index( { 'S': user } )
                            #
                            # Only remove user if this is only postal code or 
                            # the user is only associated with one postal code in this zone
                            #
                            additionalPC = False
                            if len(item['postal_code']['L']) > 1:
                                #
                                # Need to check to see if user is associated with other postal codes in this zone
                                # Get user locations from user profiles
                                #
                                rsp_item = dynamo_cli.get_item(TableName='SAFE-profiles',Key={'userid': {'S': user} })
                                if 'Item' in rsp_item:
                                    print("rsp_item: ", rsp_item['Item'])
                                    #
                                    # Look for additional matches
                                    #
                                    # Loop over Alerts
                                    #
                                    for alcl in rsp_item['Item']['alerts']['L']:
                                        #
                                        # The Alert Location is
                                        #
                                        alocation = alcl['M']['location']['S']
                                        #
                                        # Loop over User Locations to find post code
                                        #
                                        apostcode = ''
                                        for lcl in rsp_item['Item']['locations']['L']:
                                            #
                                            # match to Alert location name
                                            #
                                            if alocation == lcl['M']['name']['S']:
                                                apostcode = lcl['M']['zip']['S'] 
                                        #
                                        # Loop over Postal Codes in this Zone
                                        #
                                        for ipc in item['postal_code']['L']:
                                            #
                                            # Ignore postal_code of concern - looking for others
                                            #
                                            if ipc['S'] != postal_code:
                                                #
                                                # Does User Location Match this Zone PC?
                                                #
                                                if apostcode == ipc['S']:
                                                    additionalPC = True
                                    #
                                    # If  addtional postcodes found - then do NOT remove user from subscriber list
                                    #
                                    if additionalPC:
                                        #
                                        # Remove Response
                                        #
                                        response = 'User has multiple postal codes active in this zone - keeping user associated with this zone.'
                                        #
                                        # Return Response
                                        #
                                        result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
                                        return result
                            #
                            # If we get here then there is only one postal code for this user active in this zone
                            #
                            print("Old Subscribers: ",  item['subscribers']['L'])
                            item['subscribers']['L'].remove({'S': user})
                            print("New Subscribers: ",  item['subscribers']['L'])
                            #
                            # Put item in table
                            #
                            response = dynamo_cli.put_item(TableName='SAFE-zones', Item=item )
                            #
                            # Return Response
                            #
                            result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
                            return result

                        except:
                            #
                            # Remove Response
                            #
                            response = 'Entry does not exist for this user in this zone.'
                            #
                            # Return Response
                            #
                            result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}

                        return result
        #
        # Create Response
        #
        response = 'No Zones Found to remove user from.'
        #
        # Return Response
        #
        result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
    #
    # Create Zone Info
    #
    elif command == "create":
        #
        # If there are zones
        #
        if zone:
            #
            # Find out if item exists with this postal_code
            #
            for item in zone:
                #
                # Does item match Postal Code?
                #
                for pc in item['postal_code']['L']:
                    if pc['S'] == postal_code:
                        #
                        # Add user to subscriber list
                        #
                        try:
                            #
                            # User exists?
                            #
                            userin = item['subscribers']['L'].index( { 'S': user } )
                            #
                            # Create Response
                            #
                            response = 'Entry already exist.'
                            #
                            # Return Response
                            #
                            result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
                        except:
                            #
                            # Add User
                            #
                            print("Old Subscribers: ",  item['subscribers']['L'])
                            item['subscribers']['L'].append({'S': user})
                            print("New Subscribers: ",  item['subscribers']['L'])
                            #
                            # Put item in table
                            #
                            response = dynamo_cli.put_item(TableName='SAFE-zones', Item=item )
                            #
                            # Return Response
                            #
                            result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
                        #
                        # Return
                        #
                        return result
        #
        # new item/zone/postcode needs to be added to table
        #
        # Get Latitude & Longitude for this Postal Code
        #
        postcodeURL = '{}{}'.format(postcodeAPI,postal_code)
        with urllib.request.urlopen(postcodeURL) as geoAPI:
            geoloc = geoAPI.read()
            if geoloc is not None:
                geoloc = geoloc.decode('utf-8')
                geoloc = json.loads(geoloc)
                lat = geoloc['results'][0]['geometry']['location']['lat']
                lng = geoloc['results'][0]['geometry']['location']['lng']
        #
        # Convet Latitude and Longitude into Weather.gov zones
        #
        pointURL = '{}{},{}'.format(pointAPI,lat,lng)
        with urllib.request.urlopen(pointURL) as zoneAPI:
            zoneloc = zoneAPI.read()
            if zoneloc is not None:
                zoneloc = zoneloc.decode('utf-8')
                zoneloc = json.loads(zoneloc)
                zzone = ''
                publ = ''
                fire = ''
                for feat in zoneloc['features']:
                    if feat['properties']['type'] == 'county':
                        zzone = feat['properties']['id']
                        zname = feat['properties']['name']
                        zstate = feat['properties']['state']
                    elif feat['properties']['type'] == 'public':
                        publ = feat['properties']['id']
                    elif feat['properties']['type'] == 'fire':
                        fire = feat['properties']['id']
        #
        # Does Zone exist (without this post code)?
        #
        for item in zone:
            #
            # Zone exists?
            #
            if item['zone']['S'] == zzone:
                #
                # Add post code 
                #
                print("Old Postal Codes: ",  item['postal_code']['L'])
                item['postal_code']['L'].append({'S': postal_code})
                print("New Postal Codes: ",  item['postal_code']['L'])
                #
                # Does user already exist in Zone
                #
                try:
                    #
                    # User exists?
                    #
                    userin = item['subscribers']['L'].index( { 'S': user } )
                #
                # If not add user too
                #
                except:
                    #
                    # Add User
                    #
                    print("Old Subscribers: ",  item['subscribers']['L'])
                    item['subscribers']['L'].append({'S': user})
                    print("New Subscribers: ",  item['subscribers']['L'])
                #
                # Now Put item in table
                #
                response = dynamo_cli.put_item(TableName='SAFE-zones', Item=item )
                #
                # Return Response
                #
                result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}
                return result
        #
        # New Zone
        #
        print(" Postcode: ",postal_code )
        print(" Lattitude: ", lat, " Longitude: ", lng )
        print(" Zone: ", zzone, " Public: ", publ, " Fire: ", fire)
        #
        item = { 'zone': {'S': zzone}, 'public': {'S': publ}, 'fire': {'S': fire}, 'state': {'S': zstate}, 'name': {'S': zname}, 
                 'postal_code': {'L': [ {'S': postal_code} ] }, 'subscribers': {'L': [ { 'S': user } ] } }
        #
        # Put item in table
        #
        response = dynamo_cli.put_item(TableName='SAFE-zones', Item=item )
        #
        # Return Response
        #
        result = { "statusCode": 200, "headers":{"Content-Type": "application/json", "Access-Control-Allow-Origin" : "*"}, "body": response}

    return result