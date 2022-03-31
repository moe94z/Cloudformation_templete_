#
# Initialize app
from flask import Flask
app = Flask(__name__)

#
# Initialize routes
from app import routes
