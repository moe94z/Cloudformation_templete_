#
# routes.py
#
# Description:- Route python for Simple UI Environment Flask Application
#
# Author: Tim Hessing
# Created: 03-13-2022
# Updated: 03-13-2022
#
import os
import re
import json
import flask
import requests
import logging
import time
import urllib.request

from logging.handlers import TimedRotatingFileHandler
from flask import Flask, flash, g, redirect, render_template, request, session, abort
from flask.sessions import SecureCookieSessionInterface
from cryptography.fernet import Fernet
from datetime import datetime
from datetime import timedelta
from app import app
from urllib.parse import unquote

#
# Initialize logging
#
def ui_logger(name):
    formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')
    handler = TimedRotatingFileHandler('UI.log', when='midnight', backupCount=0)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    return logger

logger = ui_logger('UI')
logger.info("UI Initialized.")

#
# Load Configuration information
#
app.config.from_pyfile('UI.config')
config_api  = unquote('http://{}:{}'.format(app.config['LOAD_BALANCER'], app.config['CONNFIGAPI_PORT']))

#
# Setup Session
#
app.config['SECRET_KEY'] = 'this is the UI super secret'
app.config['PERMANENT_SESSION_LIFETIME'] =  timedelta(minutes=int(app.config['SESSION_TIMEOUT']))

#
# Initialize form data
#
formdata = {}
#
# Define routes
#
@app.route('/error', methods=['POST','GET'])
def errorpage():
    #
    # Show Error Page
    #
    logger.info("Error Page is error.html")
    return render_template('error.html', page='error')
#
# No Default Page/Home
#
@app.route('/', methods=['POST','GET'])
def errordef():
    #
    # Go to Error Page
    #
    logger.info("Attempt to access top-level not allowed, go to Error Page.")
    return errorpage()
#
# Configurtion Page
#
@app.route('/admin', methods=['POST','GET'])
def adminhome():
    #
    # Show Home Page
    #
    logger.info("Configuration Page is home.html for the moment.")
    return render_template('home.html', page='adminhome')
    #
    # Need to make the following work
    #
    # Get Initial Configuration
    #
    configapi = '{}/?command=read'.format(config_api)
    x = requests.post(configapi, data=formdata)

    uprofile = dynamo_cli.get_item(TableName='SAFE-profiles', Key={'userid': {'S': user} })
    if 'Item' in uprofile:
        uinfo = json.dumps(uprofile)
        uinfo = json.loads(uinfo)
        aok   = 0 # need aok = 2 for channels and locations to be defined in order to add new alarms
        linfo = []
        cinfo = []
        ainfo = []
        if 'locations' in uinfo['Item']:
            linfo = uinfo['Item']['locations']['L']
            aok = aok + 1
        if 'channels' in uinfo['Item']:
            cinfo = uinfo['Item']['channels']['L']
            aok = aok + 1
        if 'alerts' in uinfo['Item']:
            for alert in uinfo['Item']['alerts']['L']:
                alertname = alert['M']['name']['S']
                alertloc  = alert['M']['location']['S']
                alertchan = []
                for achan in alert['M']['channels']['L']:
                    cname = achan['M']['name']['S']
                    alertchan.append(cname)
                adict = {"name": alertname, "location": alertloc, "channels":  alertchan}
                ainfo.append(adict)

    return render_template('config.html', page='adminhome', aok=aok, locinfo=linfo, chaninfo=cinfo, alertinfo=ainfo)
#
@app.route('/modcfg', methods=['POST', 'GET'])
def modcfg():
    #
    # Get Form Information
    #
    formdata = request.form.to_dict(flat=False)
    action   = formdata['form_submit'][0].lower()

    configapi = '{}/?command=write'.format(config_api)
    x = requests.post(configapi, data=formdata)

    return adminhome()