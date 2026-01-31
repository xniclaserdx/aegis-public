# This file contains the web server of the application
# It is based on Flask and contains the routes for the login, register and dashboard pages
import os

from flask import Flask, redirect, render_template, request, session, url_for
from flask_socketio import SocketIO
from flask_talisman import Talisman
from flask_wtf import CSRFProtect

import app_dashboard  # Import the dashboard routes
import app_start_login_register  # Import the login and register routes
import app_usermanagement_interface  # Import the usermanagement routes

webserver_app = app_start_login_register.app # Create the Flask app beginning with the login and register routes
webserver_app.register_blueprint(app_dashboard.dashboard_routes) # Register the dashboard routes
webserver_app.register_blueprint(app_usermanagement_interface.usermanagement_routes) # Register the usermanagement routes
app_dashboard.socketio.init_app(webserver_app) # Initialize the socketio instance
app_dashboard.socketio.run(webserver_app, host='0.0.0.0', port=5000, debug=False) # Run the web server on port 5000 locally (given to nginx as a reverse proxy)