# Codename AEGIS

**Advanced Enterprise Guardian for Intrusion Security**

This repository is a sanitized public version of a university project.

[![Live Demo](https://img.shields.io/badge/demo-live-success)](https://bcsm-aegis.tech)
[![Python 3.12.7+](https://img.shields.io/badge/python-3.12.7+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-latest-green.svg)](https://flask.palletsprojects.com/)

> A real-time network anomaly detection system with machine learning capabilities, featuring secure authentication, live monitoring dashboards, and comprehensive network traffic analysis.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Usage](#usage)
- [Screenshots](#screenshots)
- [Model Training](#model-training)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

AEGIS is an advanced anomaly detection system designed to identify suspicious activities within network infrastructure in real-time. Built for the "TechCorp's IT" department, this system provides automated network monitoring using the KDD Cup 1999 dataset, which contains comprehensive network traffic data including both normal and attack patterns.

The system combines machine learning with modern web technologies to deliver a secure, scalable solution for network security monitoring.

## Features

### 🔐 Security
- **Two-Factor Authentication (2FA)**: Enhanced login security with OTP verification
- **Secure Password Management**: Password reset workflow with email verification
- **HTTPS Support**: SSL/TLS encrypted communications
- **CSRF Protection**: Built-in protection against cross-site request forgery
- **Session Management**: Secure user session handling
- **Rate Limiting**: Protection against brute force attacks

### 📊 Network Monitoring
- **Real-Time Dashboard**: Live network traffic visualization
- **Anomaly Detection**: ML-powered identification of suspicious activities
- **Data Table View**: Detailed network traffic logs and analysis
- **Model Insights**: View trained model performance and statistics

### 👥 User Management
- **User Registration**: Secure account creation with email validation
- **Role-Based Access**: Admin panel for user management
- **Activity Logging**: Track user actions and system events

### 🤖 Machine Learning
- **Neural Network Model**: PyTorch-based deep learning model
- **KDD Cup 1999 Dataset**: Trained on comprehensive network attack data
- **Real-Time Predictions**: Instant anomaly classification
- **Model Retraining**: Capability to retrain with updated data

## Project Structure
```
aegis-public/
├── templates/              # HTML templates
│   ├── dashboard.html      # Main dashboard interface
│   ├── login.html          # User login page
│   ├── register.html       # User registration page
│   ├── otp.html           # Two-factor authentication page
│   ├── resetpassword.html  # Password reset request page
│   ├── newpassword.html    # New password setup page
│   ├── usermanagement.html # Admin user management interface
│   ├── datatable.html      # Network traffic data table view
│   └── modelinfo.html      # ML model information and metrics
│
├── static/                 # Static assets
│   ├── css/               # Stylesheets
│   │   ├── dashboard.css  # Dashboard styles
│   │   ├── auth.css       # Authentication page styles
│   │   ├── register.css   # Registration page styles
│   │   ├── usermanagement.css # User management styles
│   │   ├── datatable.css  # Data table styles
│   │   └── modelinfo.css  # Model info styles
│   │
│   ├── js/                # JavaScript files
│   │   ├── dashboard.js   # Dashboard functionality
│   │   ├── usermanagement.js # User management logic
│   │   ├── datatable.js   # Data table interactions
│   │   └── modelinfo.js   # Model info scripts
│   │
│   └── favicon.ico        # Application icon
│
├── app_webserver.py       # Main Flask application server
├── app_dashboard.py       # Dashboard logic and routes
├── app_start_login_register.py # Authentication logic
├── app_usermanagement_interface.py # User management routes
├── backend_train.py       # ML model training script
├── trained_nn_model.pth   # Pre-trained neural network model
├── kddcup_data_corrected.csv # Training dataset
├── users_datastore.csv    # User database
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Technology Stack

### Backend
- **Flask**: Web framework
- **Flask-SocketIO**: Real-time bidirectional communication
- **PyTorch**: Deep learning framework for anomaly detection
- **Pandas & NumPy**: Data processing and analysis
- **Scikit-learn**: Machine learning utilities

### Frontend
- **HTML5/CSS3**: Modern web interface
- **JavaScript**: Interactive dashboard components
- **SocketIO Client**: Real-time updates

### Security
- **Flask-Talisman**: HTTPS enforcement and security headers
- **Flask-WTF**: CSRF protection
- **Werkzeug**: Password hashing and security utilities
- **Nginx**: Reverse proxy with rate limiting

### Data Visualization
- **Matplotlib**: Static data visualizations
- **Seaborn**: Statistical data visualization
- **Real-time Charts**: Live network traffic monitoring

## Prerequisites

Before setting up AEGIS, ensure you have the following installed:

- **Python 3.12.7+**: [Download](https://www.python.org/downloads/)
- **Nginx**: Web server for reverse proxy and HTTPS
  - Linux (Ubuntu/Debian): Install via `apt`
  - Windows: [Download from nginx.org](https://nginx.org/en/download.html)
- **SSL Certificate**: For HTTPS (Let's Encrypt recommended)
- **Git**: For cloning the repository
- **pip**: Python package manager (included with Python)

### System Requirements
- **RAM**: 4GB minimum (8GB recommended for model training)
- **Storage**: 2GB free space (for dataset and models)
- **OS**: Linux (Ubuntu/Debian), Windows, or macOS

## Setup Instructions

### 1. Install Nginx

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install nginx
```

**Windows:**
Download Nginx from the [official website](https://nginx.org/en/download.html) and extract to your desired location.

### 2. Obtain SSL Certificate

For production deployments with HTTPS, obtain an SSL certificate:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 3. Clone the Repository

```bash
git clone https://github.com/xniclaserdx/aegis.git
cd aegis
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Edit the `.env` file with your configuration:

```bash
# Email settings for 2FA and password reset
MAIL_USER=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587

# Secret keys (generate new ones for production!)
SECRET_KEY=your-secret-key-here
PASSWORD_PEPPER=your-pepper-key-here
```

⚠️ **Security Note**: Replace default values in `.env` with your own secure credentials before deployment.

### 6. Configure Nginx as Reverse Proxy

Create or edit Nginx configuration (`/etc/nginx/nginx.conf` or `/etc/nginx/sites-available/default`):
```nginx
worker_processes 1;

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    sendfile        on;
    keepalive_timeout 65;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=one:10m rate=10r/s;

    # Redirect HTTP to HTTPS
    server {
        listen       80;
        listen       [::]:80;
        server_name  yourdomain.com;
        
        # Block common vulnerability scanners
        location ~* (wordpress|\.php|\.xml|wp-login|wp-admin|/administrator|/configuration\.php|/joomla/|/drupal/|/CHANGELOG\.txt|/adminer\.php|/debug/|\.env|/vendor/|/phpinfo\.php|/shell\.php|\.git/|/timthumb\.php|/setup-config\.php|/api/v1|/graphql|\.bak|\.old|\.save|/backup\.sql|/db_dump\.sql) {
            return 444;
        }
        
        return 301 https://$host$request_uri;
    }

    # HTTPS server block
    server {
        listen       443 ssl;
        listen       [::]:443 ssl;
        server_name  yourdomain.com;

        # SSL certificates
        ssl_certificate "/path/to/fullchain.pem";
        ssl_certificate_key "/path/to/privkey.pem";

        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256';
        ssl_prefer_server_ciphers on;

        # Block common vulnerability scanners
        location ~* (wordpress|\.php|\.xml|wp-login|wp-admin|/administrator|/configuration\.php|/joomla/|/drupal/|/CHANGELOG\.txt|/adminer\.php|/debug/|\.env|/vendor/|/phpinfo\.php|/shell\.php|\.git/|/timthumb\.php|/setup-config\.php|/api/v1|/graphql|\.bak|\.old|\.save|/backup\.sql|/db_dump\.sql) {
            return 444;
        }

        # Proxy settings
        location / {
            limit_req zone=one burst=20 nodelay;
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        error_page   500 502 503 504  /50x.html;
        location = /50x.html {
            root   html;
        }
    }
}
```

**Important**: Replace `yourdomain.com` and certificate paths with your actual values.

### 7. Start Nginx

**Linux:**
```bash
sudo systemctl start nginx
sudo systemctl enable nginx
sudo systemctl status nginx
```

**Windows:**
Navigate to the Nginx directory and run:
```cmd
start nginx
```

### 8. Launch the Application

```bash
python app_webserver.py
```

The application will start on `http://0.0.0.0:5000` and will be accessible via Nginx at `https://yourdomain.com`.

## Usage

### First-Time Setup

1. **Access the Application**: Navigate to `https://yourdomain.com`
2. **Register an Account**: Click "Register" and create your account
3. **Verify Email**: Check your email for the verification code
4. **Complete 2FA Setup**: Enter the OTP code sent to your email
5. **Login**: Access the dashboard with your credentials

### Dashboard Navigation

- **Dashboard**: View real-time network monitoring and anomaly statistics
- **Data Table**: Browse detailed network traffic logs
- **Model Info**: View trained model architecture and performance metrics
- **User Management** (Admin only): Manage user accounts and permissions

### Password Reset

If you forget your password:
1. Click "Forgot Password" on the login page
2. Enter your email address
3. Check your email for the reset link
4. Follow the link and set a new password

## Screenshots

### Main Dashboard

**Real-Time Network Monitoring**
![Dashboard](https://codi.ide3.de/uploads/upload_94b2ff9a6ea68a587c6522fdedab020d.png)

**Network Traffic Data Table**
![Data Table](https://codi.ide3.de/uploads/upload_3caaa9bc871d2f1141c6cb41c1babdcd.png)

**Admin User Management Panel**
![Admin Panel](https://codi.ide3.de/uploads/upload_c7f42d396855cee9897eb2764de34faa.png)

**Model Architecture Overview**
![Model Overview](https://codi.ide3.de/uploads/upload_97ff932bfd3743edf6c0b6c1df815cf9.png)

### Password Reset Workflow

**Request Password Reset**
![Reset Request](https://codi.ide3.de/uploads/upload_f77a9c6d7029b020249482517525ceb6.png)

**Email Verification**
![Email Verification](https://codi.ide3.de/uploads/upload_8e138172b2bebf99fa8c8afe466a6b64.png)

**Set New Password**
![New Password](https://codi.ide3.de/uploads/upload_e3600bd8febb0a2909627566137f6f63.png)

## Model Training

The neural network model is pre-trained and included in the repository (`trained_nn_model.pth`). If you want to retrain the model:

```bash
python backend_train.py
```

### Training Details

- **Dataset**: KDD Cup 1999 (included as `kddcup_data_corrected.csv`)
- **Model Architecture**: Multi-layer neural network with PyTorch
- **Features**: 41 network traffic features
- **Classes**: Multiple attack types and normal traffic
- **Validation**: K-fold cross-validation
- **Metrics**: Accuracy, Precision, Recall, F1-Score, MCC, Cohen's Kappa

Training may take several hours depending on your hardware. The script will save the trained model to `trained_nn_model.pth`.

## Security

AEGIS implements multiple layers of security:

### Application Security
- **CSRF Protection**: Flask-WTF guards against cross-site request forgery
- **Password Hashing**: Werkzeug secure password hashing with pepper
- **Session Security**: Secure session management with secret keys
- **Input Validation**: Email validation and form input sanitization

### Network Security
- **HTTPS Only**: TLS 1.2/1.3 encryption
- **Rate Limiting**: Nginx-level request throttling (10 req/s with burst)
- **Vulnerability Scanner Blocking**: Automatic blocking of common attack patterns
- **Security Headers**: Flask-Talisman enforces security best practices

### Authentication
- **Two-Factor Authentication**: Email-based OTP verification
- **Password Requirements**: Strong password policies
- **Account Recovery**: Secure password reset workflow

⚠️ **Production Checklist**:
- [ ] Replace all default secrets in `.env`
- [ ] Use a valid SSL certificate
- [ ] Configure firewall rules
- [ ] Set up regular backups
- [ ] Monitor logs for suspicious activity
- [ ] Keep dependencies updated

## Troubleshooting

### Common Issues

**Issue**: Application won't start
```bash
# Check if port 5000 is already in use
sudo lsof -i :5000
# Kill the process if needed
sudo kill -9 <PID>
```

**Issue**: Nginx shows 502 Bad Gateway
- Ensure the Flask application is running on port 5000
- Check Nginx configuration is correct
- Verify firewall allows traffic on ports 80 and 443

**Issue**: Email verification not working
- Check MAIL_USER and MAIL_PASSWORD in `.env`
- For Gmail, enable "Less secure app access" or use an app password
- Verify SMTP settings (host, port)

**Issue**: "Permission denied" when starting Nginx
```bash
# Run with sudo on Linux
sudo systemctl start nginx
```

**Issue**: Database/CSV file errors
- Ensure `users_datastore.csv` and `log.txt` exist
- Check file permissions (should be writable)

### Getting Help

For additional support:
1. Check the GitLab CI logs for automated test results
2. Review application logs in `log.txt`
3. Verify all dependencies are installed: `pip list`
4. Check Python version: `python --version`

## Contributing

We welcome contributions to AEGIS! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**: Follow existing code style and conventions
4. **Run tests**: `python -m unittest app_unittest.py`
5. **Commit your changes**: `git commit -m "Add your feature"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a Pull Request**: Describe your changes in detail

### Code Quality

The project uses several automated checks:
- **Flake8**: PEP 8 compliance
- **Isort**: Import sorting
- **Pylint**: Code quality analysis
- **Bandit**: Security vulnerability scanning
- **Safety & Pip-Audit**: Dependency vulnerability checks


**Project Status**: Active Development  
**Last Updated**: January 2026  
**Maintained by**: @xniclaserdx

For questions or issues, please open an issue on the repository.
