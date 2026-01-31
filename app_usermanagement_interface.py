import csv
import os
import re
from datetime import datetime

from flask import Blueprint, Flask, redirect, render_template_string, request

from app_start_login_register import role_required

usermanagement_routes = Blueprint("usermanagement_routes",__name__)

CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_datastore.csv")
TXT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")

loaded_data = []

def log_event(message):
    """Log an event with timestamp to the log file."""
    with open(TXT_FILE, "a", newline="") as file:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        file.write(f'[{timestamp}] {message}\n')

def strike_users(users_list):
    """Remove users from the system and update the CSV file."""
    global loaded_data
    for user in users_list:
        for column in loaded_data:
            if user in column:
                loaded_data.remove(column)
                break
        log_event(f'User {user} successfully deleted')
    with open(CSV_FILE, "w", newline='') as target_file:
        writer = csv.writer(target_file)
        writer.writerows(loaded_data)

def new_rank(users_list):
    """Toggle user roles between admin and user for a list of users."""
    for user in users_list:
        with open(CSV_FILE, 'r') as source_file:
            reader = csv.reader(source_file)
            for row in reader:
                if user in row:
                    if 'admin' in row:
                        set_role(user, 'admin', 'user')
                    elif 'user' in row:
                        set_role(user, 'user', 'admin')

def set_role(username, old_role, new_role):
    """Change a user's role from old_role to new_role."""
    updated_rows = []
    with open(CSV_FILE, "r") as source_file:
        reader = csv.reader(source_file)
        for row in reader:
            if username in row:
                row = [re.sub(old_role, new_role, item) for item in row]
            updated_rows.append(row)
    
    with open(CSV_FILE, "w", newline='') as target_file:
        writer = csv.writer(target_file)
        writer.writerows(updated_rows)
    
    log_event(f'User {username} successfully changed role from {old_role} to {new_role}')
    return True

@usermanagement_routes.route('/usermanagement')
@role_required('admin')
def usermanagement() -> str:
    """Display the user management interface for administrators."""
    global loaded_data
    loaded_data = []
    with open(CSV_FILE, 'r') as source_file:
        reader = csv.reader(source_file)
        for column in reader:
            loaded_data.append(column)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "appoverlay_usermanagement.html")) as f:
        template = f.read()
    return render_template_string(template, data=loaded_data)

@usermanagement_routes.route('/remove_users/<users>')
@role_required('admin')
def remove_users(users):
    """Remove users from the system based on semicolon-separated list."""
    users_list = [re.sub(r'[^a-zA-Z0-9_@.]', '', user) for user in users.split(';')]
    strike_users(users_list)
    return redirect('/usermanagement')

@usermanagement_routes.route('/change_rank/<users>')
@role_required('admin')
def change_rank(users):
    """Toggle user roles between admin and user for semicolon-separated list."""
    users_list = [re.sub(r'[^a-zA-Z0-9_@.]', '', user) for user in users.split(';')]
    new_rank(users_list)
    return redirect('/usermanagement')

@usermanagement_routes.route('/change_rank/')
@role_required('admin')
def redirect_usermanagement_change_rank():
    """Redirect to usermanagement when change_rank is accessed without parameters."""
    return redirect('/usermanagement')

@usermanagement_routes.route('/remove_users/')
@role_required('admin')
def redirect_usermanagement_remove_users():
    """Redirect to usermanagement when remove_users is accessed without parameters."""
    return redirect('/usermanagement')

if __name__ == '__main__':
    app = Flask(__name__)
    app.register_blueprint(usermanagement)
    app.run(host='0.0.0.0', port=5000)