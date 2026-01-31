# Standard library imports
import csv
import hashlib
import logging
import os
import random
import re
import smtplib
import threading
import time
import uuid
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import wraps

from dotenv import load_dotenv
# Third-party imports
from flask import (Flask, Response, flash, make_response, redirect,
                   render_template, render_template_string, request, send_file,
                   session, url_for)
from flask_talisman import Talisman
from flask_wtf import CSRFProtect, FlaskForm
from itsdangerous import URLSafeTimedSerializer
from markupsafe import escape
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import HiddenField, PasswordField, StringField
from wtforms.validators import DataRequired, Email, Length

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RegistrationForm(FlaskForm): # Form for user registration using WTForms
    email = StringField('Email', validators=[DataRequired(), Email()], default='')
    password = PasswordField('Password', validators=[DataRequired(), Length(min=8)])
    role = HiddenField('Role', default='user')

class LoginForm(FlaskForm): # Form for user login using WTForms
    email = StringField('Email', validators=[DataRequired(), Email()], default='')
    password = PasswordField('Password', validators=[DataRequired()])

class ResetPasswordRequestForm(FlaskForm): # Form for requesting a password reset using WTForms
    email = StringField('Email', validators=[DataRequired(), Email()], default='')

class ResetPasswordForm(FlaskForm): # Form for resetting a password using WTForms     
    password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])

class VerifyCodeForm(FlaskForm): # Form for verifying a code using WTForms
    verification_code = StringField('Verification Code', validators=[DataRequired()])

load_dotenv()

# Flask app setup
app = Flask(__name__, template_folder='.')

# Rate limiting configuration
RATE_LIMIT = {} # Rate limit dictionary
RATE_LIMIT_PERIOD = 60  # Rate limit period in seconds
MAX_ATTEMPTS = 15 # Maximum number of attempts before rate limiting

# Session and authentication constants
SESSION_LIFETIME_SECONDS = 1800  # 30 minutes
VERIFICATION_CODE_MIN = 100000  # 6-digit verification code minimum
VERIFICATION_CODE_MAX = 999999  # 6-digit verification code maximum
VERIFICATION_CODE_EXPIRY_SECONDS = 120  # 2 minutes
PASSWORD_RESET_TOKEN_EXPIRY_SECONDS = 300  # 5 minutes

# CSRF Protection
csrf = CSRFProtect(app) # CSRF protection for the application

# Secret key must be set via environment variable for security
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable must be set")
app.config['SECRET_KEY'] = SECRET_KEY
serializer = URLSafeTimedSerializer(app.config['SECRET_KEY']) # Serializer for the secret key

# CSRF protection enabled by default (can be disabled for testing only)
app.config['CSRF_ENABLED'] = os.getenv('CSRF_ENABLED', 'True') == 'True'

# Session configuration 
app.config['SESSION_COOKIE_SECURE'] = True # Secure session cookie
app.config['SESSION_COOKIE_HTTPONLY'] = True # HTTP only session cookie
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # SameSite cookie policy
app.config['SESSION_COOKIE_NAME'] = '__Secure-session' # Session cookie name
app.config['PERMANENT_SESSION_LIFETIME'] = SESSION_LIFETIME_SECONDS # Session lifetime in seconds

# Pepper for password hashing
PEPPER = os.getenv("PASSWORD_PEPPER")

# Content Security Policy (CSP) configuration for Talisman
csp = {
    'default-src': "'self'",
    'script-src': "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdn.socket.io https://code.jquery.com https://cdn.datatables.net https://cdnjs.cloudflare.com/ajax/libs/crypto-js/4.0.0/crypto-js.min.js",
    'style-src': "'self' 'unsafe-inline' https://fonts.googleapis.com",
    'img-src': "'self' data: https:",
    'font-src': "'self' https://fonts.gstatic.com",
    'connect-src': "'self' ws://localhost:5000 wss://localhost:5000",
    'frame-src': "'self'",
    'object-src': "'none'",
    'form-action': "'self'",
}

Talisman(app, content_security_policy=csp) # Apply the CSP to the application

# File paths for data storage and logging
CSV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "users_datastore.csv")
TXT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log.txt")

# Email configuration for sending verification codes
MAIL_USER = os.environ.get('MAIL_USER')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
MAIL_HOST = "smtp.gmail.com"
MAIL_PORT = 587

# Global variables for session management
banned_ip_for_run = [] # Banned IP addresses
session_store = {} # Session store
coupon_store = [] # Coupon store
reset_password_tokens = [] # Reset password tokens
reset_password_tokens_expiry = [] # Reset password token expiry

def session_garbage_collector_thread():
    """Remove expired sessions from memory."""
    """Remove expired reset password tokens from memory."""
    try:
        while True:
            global session_store, reset_password_tokens
            current_time = time.time()
            # Remove expired sessions from memory
            expired_sessions = [session_token for session_token, session_data in session_store.items() if session_data['expiry'] < current_time]
            for session_token in expired_sessions:
                del session_store[session_token]
            
            # Remove expired reset password tokens from memory
            expired_reset_password_tokens = [reset_token for reset_token in reset_password_tokens if reset_token['expiry'] < current_time]
            for reset_token in expired_reset_password_tokens:
                reset_password_tokens.remove(reset_token)

            time.sleep(60) # Check every 60 seconds
    except:
        shutdown_webserver("Failed to run session garbage collector thread.")

# Start the session garbage collector thread as a daemon
session_garbage_collector_thread = threading.Thread(target=session_garbage_collector_thread, daemon=True)
session_garbage_collector_thread.start()

def extend_session(response):
    """Extend the session duration."""
    cookie = request.cookies.get('logged_in') # Get the session cookie
    response.set_cookie('logged_in', cookie, secure=True,
                                httponly=True, samesite='Lax', expires=time.time() + 1800) # Extend the session duration 
    return response # Return the response

def is_valid_email(email):
    """Validate email format."""
    return re.match(r"[^@]+@[^@]+\.[^@]+", email) is not None

def store_session(cookie_value, user_email, user_role, time):
    """Store session details in memory with the variables email, role and expiry."""
    session_store[cookie_value] = {'email': user_email, 'role': user_role, 'expiry': time} 
    
def get_session(cookie_value):
    """Retrieve session details from memory."""
    return session_store.get(cookie_value)

def remove_session(cookie_value):
    """Remove session details from memory."""
    if cookie_value in session_store:
        del session_store[cookie_value]

def get_session_role(cookie_value):
    """Get the role of the user from the session."""
    session_data = get_session(cookie_value)
    if session_data:
        return session_data.get('role')
    return None

def get_session_email(cookie_value):
    """Get the email of the user from the session."""
    session_data = get_session(cookie_value)
    if session_data:
        return session_data.get('email')
    return None

def send_email(email, subject, body, is_html=False):
        """Send an email to the user."""
        if not is_valid_email(email):
            return "Invalid email address.", 400

        msg = MIMEMultipart()
        msg['From'] = MAIL_USER
        msg['To'] = email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html' if is_html else 'plain'))

        log_event(f'Attempting to send email to {email} at {datetime.now()}')

        try:
            with smtplib.SMTP(MAIL_HOST, MAIL_PORT) as server:
                server.starttls()
                server.login(MAIL_USER, MAIL_PASSWORD)
                server.send_message(msg)
            log_event(f'Successfully sent email to {email}')
            flash('Email sent successfully.', 'success')
        except smtplib.SMTPException as e:
            shutdown_webserver(f"Failed to send email: {str(e)}")

def send_verification_code(email, code):
    """Send a verification code to the user's email."""
    body = f"""
    Hello,

    Your verification code is: <strong>{code}</strong>

    Please enter this code in the application to complete the verification process.
    The corresponding coupon value will expire in 2 minutes.
    Once the coupon expires, you will need to log in again.

    Thank you!
    """
    send_email(email, '2-Factor Authentication Code', body, is_html=True)

def send_reset_password_email(email, token):
    """Send a reset password email to the user."""
    reset_url = url_for('reset_password', token=token, _external=True)
    body = f"Click the following link to reset your password:\n\n{reset_url}"
    send_email(email, 'Reset Your Password', body)

def log_event(message): # Function to log events to a text file
    try:
        with open(TXT_FILE, "a", newline="") as file:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            file.write(f'[{timestamp}] {message}\n')
    except Exception as e:
        logger.error(f"Failed to log event: {str(e)}")

def get_user_attribute(user_data, attribute):
    try:
        """Access user attributes from CSV data."""
        valid_attributes = ['register', 'email', 'hashed_password', 'role'] 
        if attribute not in valid_attributes or not isinstance(user_data, dict):
            return None
        return user_data.get(attribute, None)
    except:
        shutdown_webserver("Failed to get user attribute.")

def rate_limit(func):
    @wraps(func)
    def wrapper(*args, **kwargs): 
        global banned_ip_for_run # Global variable for banned IP addresses
        ip = request.remote_addr # Get the IP address of the request
        current_time = time.time()
        if ip in RATE_LIMIT:
            if current_time - RATE_LIMIT[ip]['timestamp'] < RATE_LIMIT_PERIOD: 
                # Check if the time since the last request is less than the rate limit period
                if RATE_LIMIT[ip]['attempts'] >= MAX_ATTEMPTS and RATE_LIMIT[ip]['attempts'] < MAX_ATTEMPTS + 30: 
                    # Check if the number of attempts is greater than the maximum attempts and less than the maximum attempts plus 30
                    RATE_LIMIT[ip]['attempts'] += 1 
                    # Increment the number of attempts if the rate limit is not exceeded
                    return "Too many attempts. Please try again later.", 429 
                # Return a 429 status code if the rate limit is exceeded
                elif RATE_LIMIT[ip]['attempts'] >= MAX_ATTEMPTS + 30: 
                    # Check if the number of attempts is greater than the maximum attempts plus 30
                    banned_ip_for_run.append(ip) 
                    # Ban the IP address if the rate limit is exceeded
                    return "You have been banned for too many attempts. Your request will not be answered anymore.", 429 
                # Ban the IP address if the rate limit is exceeded
                RATE_LIMIT[ip]['attempts'] += 1 
                # Increment the number of attempts if the rate limit is not exceeded
            else:
                RATE_LIMIT[ip] = {'timestamp': current_time, 'attempts': 1} 
                # Reset the rate limit if the time since the last request is greater than the rate limit period
        else:
            RATE_LIMIT[ip] = {'timestamp': current_time, 'attempts': 1} 
            # Set the rate limit if the IP address is not in the rate limit dictionary
        return func(*args, **kwargs)
    return wrapper

def role_required(*roles):
    """Decorator to restrict access based on user roles."""
    def wrapper(func): 
        @wraps(func) 
        def decorated_view(*args, **kwargs): 
            try:    
                cookie_value = request.cookies.get("logged_in") 
                # Get the session cookie
                session_data = get_session(cookie_value) 
                # Get the session data
                session_role = session_data.get('role') if session_data else None 
                # Get the role of the user from the session
                if not session_data or session_role not in roles: 
                    # Check if the user is not logged in or the role is not authorized (roles are passed as arguments)
                    return "Your role is not authorized to access this page or you are not logged in.", 403 
                # Return a 403 status code if the role is not authorized
                return func(*args, **kwargs) 
            # Return the function if the role is authorized
            except:
                shutdown_webserver("Failed to check user role.")
        return decorated_view
    return wrapper

def is_password_strong(password):
    """Check if the password meets the strength requirements."""
    if len(password) < 8:
        return False, "The password must be at least 8 characters long.", "weak"
    if not re.search(r"[A-Z]", password):
        return False, "The password must contain at least one uppercase letter.", "weak"
    if not re.search(r"[a-z]", password):
        return False, "The password must contain at least one lowercase letter.", "weak"
    if not re.search(r"[0-9]", password):
        return False, "The password must contain at least one digit.", "medium"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "The password must contain at least one special character.", "medium"
    return True, "", "strong"

def create_user_dict(user_data): 
    """Maps CSV data to a user dictionary for attribute access."""
    try:
        if len(user_data) < 4:
            return None
        return {
            'email': user_data[0],
            'hashed_password': user_data[1],
            'role': user_data[2],
            'is_verified': user_data[3]
        }
    except:
        shutdown_webserver("Failed to create user dictionary.")

def validate_email(email):
    """Validate the email address."""
    if email:
        log_event(f'Invalid email address: {email}')
        if re.search(r'[<>\"\'%;()&]', email) or not is_valid_email(email):
            log_event(f'Harmful characters detected in email: {email}')
            return False
    return True

def validate_password(password):
    """Validate the password strength."""
    return is_password_strong(password)[0]

def is_email_registered(email):
    """Check if the email is already registered."""
    try:
        with open(CSV_FILE, "r") as file:
            reader = csv.reader(file)
            users = [create_user_dict(user) for user in reader]
            for user in users:
                if user.get('email') == email:
                    log_event(f'Registration attempt with already registered email: {email}')
                    flash('Email address already registered.', 'error')
                    return True
    except Exception as e:
        logger.error(f"Failed to read user data: {str(e)}")
    return False

def register_user(email, password):
    """Register a new user."""
    hashed_password = hash_password(password, email)
    try:
        with open(CSV_FILE, "a", newline="") as file:
            is_verified = "0"
            writer = csv.writer(file)
            writer.writerow([email, hashed_password, "user", is_verified])
        log_event(f'New registration for {email} with role user')
        return True
    except Exception as e:
        logger.error(f"Failed to write user data: {str(e)}")
        log_event(f'Failed to write user data at {datetime.now()}')
        return False

def validate_login_email(email):
    """Validate the email address for login."""
    if email:
        log_event(f'Invalid email address: {email}')
        if re.search(r'[<>\"\'%;()&]', email) or not is_valid_email(email):
            log_event(f'Harmful characters detected in email: {email}')
            return False
    return True

def get_users_from_csv():
    """Retrieve users from the CSV file."""
    try:
        with open(CSV_FILE, "r") as file:
            reader = csv.reader(file)
            return [create_user_dict(user) for user in reader]
    except Exception as e:
        logger.error(f"Failed to read user data: {str(e)}")
        return None

def authenticate_user(users, email, password):
    """Authenticate the user with the provided email and password."""
    for user in users:
        try:
            hashed_password = user['hashed_password']
            if hashlib.sha256((password + PEPPER + email).encode()).hexdigest() == hashed_password and user['email'] == email:
                return user
        except:
            shutdown_webserver("Failed to authenticate user.")
    return None

def initiate_verification(user, form):
    """Initiate the verification process for the authenticated user."""
    email = user['email']
    response = prepare_verification_response(form)
    coupon_cookie_value = generate_coupon_cookie(response)
    session_token = generate_session_token()
    verification_code = generate_verification_code()
    send_verification_code(email, verification_code)
    store_verification_coupon(user, coupon_cookie_value, session_token, verification_code)
    return response

def prepare_verification_response(form):
    """Prepare the response for the verification process."""
    return make_response(render_template('appoverlay_otp.html', form=form))

def generate_coupon_cookie(response):
    """Generate a coupon cookie and set it in the response."""
    coupon_cookie_value = str(random.randint(100000, 999999))
    response.set_cookie('coupon', coupon_cookie_value, secure=True,
                        httponly=False, samesite='Lax', expires=time.time() + 120)
    return coupon_cookie_value

def generate_session_token():
    """Generate a unique session token."""
    return str(uuid.uuid4())

def generate_verification_code():
    """Generate a random verification code."""
    return str(random.randint(100000, 999999))

def store_verification_coupon(user, coupon_cookie_value, session_token, verification_code):
    """Store the verification coupon in the global coupon store."""
    global coupon_store
    verification_coupon = {
        'verify_code': hashlib.sha256(verification_code.encode()).hexdigest(),
        'session_token': session_token,
        'email': user['email'],
        'password': user['hashed_password'],
        'role': user.get('role'),
        'coupon_cookie': coupon_cookie_value
    }
    coupon_store.append(verification_coupon)

def get_verification_coupon(coupon):
    global coupon_store
    try:
        for verification_coupon in coupon_store:
            if verification_coupon['coupon_cookie'] == coupon:
                coupon_store.remove(verification_coupon)
                return verification_coupon
    except:
        shutdown_webserver("Failed to verify code.")
    return None

def is_correct_code(entered_code, correct_code):
    try:
        return entered_code.isdigit() and hashlib.sha256(entered_code.encode()).hexdigest() == correct_code
    except:
        shutdown_webserver("Failed to verify code.")
    return False

def login_user(response, verification_coupon):
    try:
        email = verification_coupon['email']
        session_token = verification_coupon['session_token']
        role = verification_coupon['role']
        store_session(session_token, email, role, time.time() + 1800)
        response.set_cookie('logged_in', session_token, secure=True,
                            httponly=False, samesite='Lax', expires=time.time() + 1800)
        log_event(f"User {email} logged in with role {role}")
        return response
    except:
        shutdown_webserver("Failed to log in user.")

def generate_reset_token(email):
    """Generate a reset token for the user."""
    try:
        token = hashlib.sha256((email + app.config['SECRET_KEY']+ str(random.randint(100000, 999999))).encode()).hexdigest()
        reset_token = {
            'token': token,
            'email': email,
            'expiry': time.time() + 300
        } 
        return reset_token
    except:
        shutdown_webserver("Failed to generate reset token.")

def validate_reset_email(email):
    """Validate the email address for reset password request."""
    if re.search(r'[<>\"\'%;()&]', email) or not is_valid_email(email):
        log_event(f'Harmful characters detected in email: {email}')
        return False
    return True

def user_exists(users, email):
    """Check if the user exists in the CSV data."""
    return any(user and user.get('email') == email for user in users)

def process_reset_request(email):
    """Process the password reset request."""
    global reset_password_tokens
    token = generate_reset_token(email)
    reset_password_tokens.append(token)
    send_reset_password_email(token['email'], token['token'])
    log_event(f'Password reset requested for {token["email"]}')
    return "Password reset instructions have been sent to your email address."

def find_reset_token(token):
    """Find the reset token in the global reset_password_tokens list."""
    global reset_password_tokens
    for reset_token in reset_password_tokens:
        if reset_token['token'] == token:
            return reset_token
    return None

def hash_password(password, email):
    """Hash the password with the email and PEPPER."""
    return hashlib.sha256((password + PEPPER + email).encode()).hexdigest()

def update_user_password(email, hashed_password):
    """Update the user's password in the CSV file."""
    users = []
    with open(CSV_FILE, "r") as file:
        reader = csv.reader(file)
        for user_data in reader:
            user = create_user_dict(user_data)
            if email == user.get('email'):
                user_data[1] = hashed_password
            users.append(user_data)
    with open(CSV_FILE, "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(users)

def remove_reset_token(reset_token):
    """Remove the reset token from the global reset_password_tokens list."""
    global reset_password_tokens
    reset_password_tokens.remove(reset_token)

def shutdown_webserver(message):
    """Shutdown the web app and log the error message. Is called in case of an critical error to prevent further damage."""
    logger.critical(f"{message}")
    logger.critical("Application safety not guaranteed. Please check the log file for more information.")
    log_event(f"Shutting down the application. {message}")
    os._exit(1)
        
@app.route("/")
def index():
    return redirect(url_for('login')) # Redirect to the login page by default

@app.route("/register", methods=["GET", "POST"])
@rate_limit
@csrf.exempt
def register():
    try:
        form = RegistrationForm() # Create a registration form
        if form.validate_on_submit(): # Check if the form is submitted
            email = form.email.data # Get the email from the form
            password = form.password.data # Get the password from the form

            if not validate_email(email):
                return "Invalid characters in email address.", 400

            if not validate_password(password):
                return is_password_strong(password)[1], 400

            if is_email_registered(email):
                return "Email address already registered.", 400

            if not register_user(email, password):
                return "Currently unavailable.", 503

            return f"Registration successful. Go to <a href='{url_for('login')}'>login</a> page.", 200
        return render_template('appoverlay_register.html', form=form)
    except:
        shutdown_webserver("Failed to register user.")

    
@app.route("/login", methods=["GET", "POST"])
@rate_limit
@csrf.exempt
def login():
    form = LoginForm()
    try:
        if form.validate_on_submit():
            email = form.email.data
            password = form.password.data
            if not validate_login_email(email):
                return "Invalid characters in email address.", 400
            users = get_users_from_csv()
            if users is None:
                return "Currently unavailable.", 503
            user = authenticate_user(users, email, password)
            if user:
                return initiate_verification(user, form)
            else:
                log_event(f'Failed login attempt for email: {email}')
                return "Invalid password or user already logged in.", 401
        else:
            return render_template('appoverlay_login.html', form=form)
    except:
        shutdown_webserver("Failed to log in user.")


@app.route("/verify_code", methods=["POST"])
@csrf.exempt
@rate_limit
def verify_code():
    try:
        response = make_response(redirect("dashboard"))
        coupon = request.cookies.get('coupon')
        if not coupon:
            return "Invalid coupon.", 401

        verification_coupon = get_verification_coupon(coupon)
        if not verification_coupon:
            return "Invalid coupon.", 401

        form = VerifyCodeForm()
        if form.validate_on_submit():
            entered_code = form.verification_code.data
            if is_correct_code(entered_code, verification_coupon['verify_code']):
                return login_user(response, verification_coupon)
            else:
                return "Invalid verification code.", 401
        return render_template('appoverlay_otp.html', form=form)
    except:
        shutdown_webserver("Failed to verify code.")


@app.route("/admin_access")
@role_required('admin')
def admin_panel():
    """Debugging route to check if the admin panel is accessible."""
    return "You have access to the admin panel and your role is admin."

@app.route("/user_access")
@role_required('user', 'admin')
def user_dashboard():
    """Debugging route to check if the user dashboard is accessible."""
    return "You have access to the user dashboard and your role is user."

# Function to check active sessions as an admin
@app.route("/get_active_sessions")
@role_required('admin')
def get_active_sessions():
    """Get the active sessions as an admin."""
    try:
        return str(session_store)
    except:
        shutdown_webserver("Failed to get active sessions.")

@app.route("/logout")
@role_required('user', 'admin')
def logout():
    try:
        cookie_value = request.cookies.get("logged_in") # Get the session cookie
        if cookie_value:
            remove_session(cookie_value) # Remove the session data from memory
            log_event("User logged out")
            response = make_response("Logged out sucessfully!")
            response.set_cookie('logged_in', '', expires=1) # Remove the session cookie
        return response
    except:
        shutdown_webserver("Failed to log out user.")

@app.route("/reset_password_request", methods=["GET", "POST"])
@rate_limit
@csrf.exempt
def reset_password_request():
    """Request a password reset."""
    form = ResetPasswordRequestForm()
    try:
        if form.validate_on_submit():
            email = form.email.data
            if not validate_reset_email(email):
                return "Invalid characters in email address.", 400
            users = get_users_from_csv()
            if users is None:
                return "Currently unavailable.", 503
            if not user_exists(users, email):
                return "Email address not found.", 406
            return process_reset_request(email)
        return render_template('appoverlay_resetpassword.html', form=form)
    except:
        shutdown_webserver("Failed to reset password.")


@app.route("/reset_password/<token>", methods=["GET", "POST"])
@csrf.exempt
@rate_limit
def reset_password(token):
    try:
        form = ResetPasswordForm()
        global reset_password_tokens
        reset_token = find_reset_token(token)
        if not reset_token:
            return "Invalid or expired reset token.", 400

        if form.validate_on_submit():
            new_password = form.password.data
            email = reset_token['email']
            hashed_password = hash_password(new_password, email)
            update_user_password(email, hashed_password)
            remove_reset_token(reset_token)
            log_event(f'Password successfully reset for {email}')
            return redirect(url_for('login'))
        return render_template('appoverlay_newpassword.html', form=form)
    except:
        shutdown_webserver("Failed to reset password.")

@app.errorhandler(404)
@rate_limit
def page_not_found(e):
    """Error handler for 404 Not Found. Say that the page is not found and that the user may be rate limited or banned."""
    return "Page not found. If you request request unavailable content multiple times, you may be rate limited or even banned.", 410

@app.route('/robots.txt')
def robots():
    """Return a robots.txt file allowing all user agents to access the site."""
    content = "User-agent: *\nDisallow:"
    return Response(content, mimetype='text/plain', status=200)

@app.before_request
def before_request():
    """Check if the IP address is banned before processing the request. 
    If the IP address is banned, return a 444 status code and do not process the request to save resources."""
    global banned_ip_for_run
    if request.remote_addr in banned_ip_for_run:
        return "", 444
    
@app.route('/favicon.ico')
def favicon():
    return send_file('favicon-32x32.ico')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
