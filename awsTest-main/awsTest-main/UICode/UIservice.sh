#!/bin/sh -x
#
# UIservice.
#
# chkconfig: - 85 15
# description: This script starts and stops the Simple UI Environment Script
#
# Author: Mohamad Quteifan
# Created: 03-13-2022
# Updated: 03-13-2022
#
# Activate Environment
#
source /UI/UIEenv/bin/activate
#
# Define Enviroment Variables
#
export FLASK_APP=SimpleUIEnvironment.py
export FLASK_ENV=development
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
#
# Move to UI Launch Directory
#
cd /UI/
#
# Run UI output to log
#
systemctl restart nginx
flask run --host=127.0.0.1 --port=5000
#
# Done
#
exit 0
