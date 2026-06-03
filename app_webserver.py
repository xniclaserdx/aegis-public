import app_dashboard  # Import the dashboard routes
import app_start_login_register  # Import the login and register routes
import app_usermanagement_interface  # Import the usermanagement routes

webserver_app = app_start_login_register.app # Create the Flask app beginning with the login and register routes
webserver_app.register_blueprint(app_dashboard.dashboard_routes) # Register the dashboard routes
webserver_app.register_blueprint(app_usermanagement_interface.usermanagement_routes) # Register the usermanagement routes
app_dashboard.socketio.init_app(webserver_app) # Initialize the socketio instance

def create_app():
    """Return the configured Flask application for tests and WSGI servers."""
    return webserver_app

if __name__ == '__main__':
    # Run the web server on port 5000 locally (given to nginx as a reverse proxy).
    app_dashboard.socketio.run(webserver_app, host='0.0.0.0', port=5000, debug=False)
