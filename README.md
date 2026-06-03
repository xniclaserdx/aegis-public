# AEGIS

**Advanced Enterprise Guardian for Intrusion Security**

[![CI](https://github.com/xniclaserdx/aegis-public/actions/workflows/ci.yml/badge.svg)](https://github.com/xniclaserdx/aegis-public/actions/workflows/ci.yml)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-web%20app-green.svg)](https://flask.palletsprojects.com/)

AEGIS is a public showcase version of a university project for network anomaly detection. It combines a Flask dashboard, authentication flow, real-time Socket.IO updates, and a PyTorch model trained around KDD Cup 1999-style network traffic data.

This repository is intended to demonstrate project structure, applied machine learning, web security basics, and end-to-end product thinking. It is not presented as a production-ready security appliance.

## Highlights

- Flask web application with login, registration, password reset, OTP verification, and role-based pages.
- Real-time dashboard powered by Flask-SocketIO.
- PyTorch neural network model for simulated network traffic classification.
- Admin user-management view backed by CSV-based local storage.
- Security controls including Flask-WTF CSRF protection, HttpOnly cookies, Werkzeug password hashing, CSP headers, and optional HTTPS enforcement.
- Lightweight GitHub Actions checks for syntax and authentication-template smoke tests.

## Project Structure

```text
aegis-public/
  app_webserver.py                 # Application entry point
  app_start_login_register.py      # Authentication, sessions, email, password reset
  app_dashboard.py                 # Dashboard routes and traffic simulation
  app_usermanagement_interface.py  # Admin user-management routes
  backend_train.py                 # Model training script
  app_unittest.py                  # Unit tests
  trained_nn_model.pth             # Pre-trained PyTorch model
  kddcup_data_corrected.csv        # Dataset tracked through Git LFS
  requirements.txt                 # Python dependencies
  templates/                       # HTML templates
  static/                          # CSS, JavaScript, favicon
  .github/workflows/ci.yml         # Lightweight GitHub Actions checks
```

Runtime files such as `log.txt` and `users_datastore.csv` are intentionally ignored. They are created locally by the application as needed.

## Requirements

- Python 3.12
- Git LFS for the dataset
- Optional: Nginx and a TLS certificate for production-style HTTPS deployment

Install Git LFS before cloning or pull the LFS object after cloning:

```bash
git lfs install
git lfs pull
```

Without Git LFS, `kddcup_data_corrected.csv` will only be a small pointer file and the dashboard/model-loading path will not have the real dataset available.

## Quick Start

```bash
git clone https://github.com/xniclaserdx/aegis-public.git
cd aegis-public

git lfs install
git lfs pull

python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` before starting the app:

```env
SECRET_KEY=replace-with-a-random-secret
PASSWORD_PEPPER=replace-with-a-random-pepper
MAIL_USER=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_HOST=smtp.gmail.com
MAIL_PORT=587
FORCE_HTTPS=False
WTF_CSRF_ENABLED=True
```

For local development, keep `FORCE_HTTPS=False`. For a production-style deployment behind TLS/Nginx, set it to `True`.

Start the application:

```bash
python app_webserver.py
```

The Flask/Socket.IO app runs on port `5000`.

## Usage

1. Register a user account.
2. Complete the OTP verification flow through the configured email account.
3. Open the dashboard and start the traffic simulation.
4. Review recent traffic rows in the data table.
5. Inspect model details and the model file hash.

Admin-only user-management routes require an account with the `admin` role in the local CSV store.

## Model And Data

The repository includes a pre-trained model file, `trained_nn_model.pth`. The larger KDD Cup 1999-derived dataset is tracked through Git LFS as `kddcup_data_corrected.csv`.

To retrain the model:

```bash
python backend_train.py
```

Training can be slow depending on hardware and dataset availability. The script writes the updated model checkpoint to `trained_nn_model.pth`.

## Security Notes

AEGIS includes security-oriented application controls suitable for a university/demo project:

- CSRF protection through Flask-WTF.
- Password hashing through Werkzeug, with an application-level pepper.
- HttpOnly secure cookies for login and OTP flow state.
- Content Security Policy headers through Flask-Talisman.
- Optional HTTPS enforcement for reverse-proxy deployments.
- Basic in-memory rate limiting for sensitive routes.

Important limitations:

- User storage is CSV-based and intended for demo use, not production.
- Sessions and reset tokens are stored in memory and are lost on process restart.
- Email-based OTP depends on correctly configured SMTP credentials.
- The model simulation is based on historical benchmark data and should not be treated as live IDS coverage.

## Checks

Lightweight checks run in GitHub Actions on push and pull request. Locally, you can run:

```bash
python -m py_compile app_webserver.py app_start_login_register.py app_dashboard.py app_usermanagement_interface.py backend_train.py app_unittest.py
```

Full unit tests require a working PyTorch installation and the Git LFS dataset:

```bash
python -m unittest app_unittest.py
```

## Troubleshooting

If the app cannot load the dataset, run:

```bash
git lfs pull
```

If email verification fails, check the SMTP values in `.env`. For Gmail, use an app password.

If the app redirects to HTTPS during local development, set:

```env
FORCE_HTTPS=False
```

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
