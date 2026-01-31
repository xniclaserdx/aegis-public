import hashlib
import os
import threading
import time
from collections import deque
from datetime import datetime

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from flask import (Blueprint, Flask, jsonify, render_template_string, request,
                   send_file, url_for)
from flask_socketio import SocketIO
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import Dataset

from app_start_login_register import (get_session_email, get_session_role,
                                      rate_limit, role_required)

dashboard_routes = Blueprint("dashboard_routes",__name__)
socketio = SocketIO()

# Enable X-Sendfile to serve static files via the web server (e.g., Nginx)
model_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained_nn_model.pth")

# Dataset definition needed for the simulation 
class NetDataset(Dataset):
    def __init__(self, data):
        # Preload features and labels as tensors and drop the target column
        self.features = torch.tensor(data.drop('label', axis=1).values, dtype=torch.float32)
        self.labels = torch.tensor(data['label'].values, dtype=torch.long)
    def __len__(self):
        return len(self.features)
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx] # Return features and labels as tensors

# Simple Neural Network needed for the simulation needed for initialization of the model
class SimpleNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(SimpleNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        self.softmax = nn.LogSoftmax(dim=1)
    def forward(self, x): # Forward pass of the neural network
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.softmax(self.fc3(x))
    def reset_parameters(self): # Reset the parameters of the neural network
        for layer in self.children():
            if hasattr(layer, 'reset_parameters'):
                layer.reset_parameters()

# Training class needed for the simulation as part of the model initialization
class DataSimulator:
    def __init__(self, model, df, df_copy, label_enc, le_encoders, scaler):
        self.model = model # Neural network model
        self.df = df # Original dataset standardized for model input
        self.df_copy = df_copy # Copy of the original dataset for display purposes
        self.label_enc = label_enc # Label encoder for the target column
        self.le_encoders = le_encoders # Label encoders for the categorical columns
        self.scaler = scaler # Standard scaler for the dataset
        self.last_120_rows = deque(maxlen=120)  # Using deque for FIFO efficiency
        self.normal_count = 0 # Counter for normal traffic
        self.bad_count = 0 # Counter for bad traffic (attacks)
        self.label_mapping = {i: label for i, label in enumerate(label_enc.classes_)}  # Initialize once
        self.df_normal = df[df['label'] == label_enc.transform(['normal.'])[0]]  # Filter normal traffic data
        self.df_attack = df[df['label'] != label_enc.transform(['normal.'])[0]]  # Filter attack traffic data
        self.uuid = None # UUID for the simulation instance to compare with the user UUID and display if matches

    def simulate_incoming_data(self, stop_event: threading.Event) -> None:
        while not stop_event.is_set():
            try:
                uuid = self.uuid
                current_time = datetime.now().strftime('%H:%M:%S')
                row, original_row = self.get_random_row()
                update_data = self.prepare_update_data(current_time, original_row)
                predicted_label_str = self.predict_label(row)
                self.update_counters(predicted_label_str)
                bad_traffic_percentage = self.calculate_bad_traffic_percentage()
                self.update_data(update_data, predicted_label_str, bad_traffic_percentage, uuid)
                socketio.emit('update_data', update_data)
                self.update_last_120_rows(current_time, original_row, predicted_label_str)
                time.sleep(1)
            except Exception:
                return None

    def get_random_row(self):
        if np.random.rand() < 0.08:
            row = self.df_attack.sample(n=1).iloc[0]
        else:
            row = self.df_normal.sample(n=1).iloc[0]
        original_row = self.df_copy.loc[row.name]
        return row, original_row

    def update_counters(self, predicted_label_str):
        if predicted_label_str == 'normal.':
            self.normal_count += 1
        else:
            self.bad_count += 1

    def calculate_bad_traffic_percentage(self):
        total_count = self.normal_count + self.bad_count
        return (self.bad_count / total_count) * 100 if total_count > 0 else 0

    def update_data(self, update_data, predicted_label_str, bad_traffic_percentage, uuid):
        update_data.update({
            'predicted_label': predicted_label_str,
            'normal_count': self.normal_count,
            'bad_count': self.bad_count,
            'bad_traffic_percentage': bad_traffic_percentage,
            'uuid': hashlib.sha256(uuid.encode()).hexdigest()
        })

    def predict_label(self, row: pd.Series) -> str:
        try:
            input_data = torch.tensor(row.values[:-1], dtype=torch.float32).unsqueeze(0) # Prepare the input data for the model
            with torch.no_grad(): # Disable gradient calculation for inference
                prediction = self.model(input_data) # Get the prediction from the model
                predicted_label = prediction.argmax(dim=1).item() # Get the predicted label
            return self.label_mapping.get(predicted_label, "Unknown") # Return the predicted label as a string
        except Exception:
            return "Unknown"

    def update_last_120_rows(self, current_time: str, original_row: pd.Series, predicted_label_str: str) -> None:
        try:
            new_row = original_row.copy() # Copy the original row for display purposes
            new_row['timestamp'] = current_time # Update the timestamp in the new row
            new_row['predicted_label'] = predicted_label_str # Update the predicted label in the new row
            new_row['label'] = self.label_enc.inverse_transform([int(original_row['label'])])[0] # Update the real label in the new row
            self.last_120_rows.append(new_row) # Append the new row to the last 120 rows
        except:
            return None

    def prepare_update_data(self, current_time: str, original_row: pd.Series) -> dict:
        # Generate a timestamp
        # Load the data from the original row and transform it with type information
        # The data is updated in simulate incoming data with predicted label, real label, normal count, bad count, bad traffic percentage, and UUID
        return {
            'timestamp': current_time, 
            'duration': int(original_row['duration']),
            'protocol_type': self.le_encoders['protocol_type'].inverse_transform([int(original_row['protocol_type'])])[0],
            'service': self.le_encoders['service'].inverse_transform([int(original_row['service'])])[0],
            'flag': self.le_encoders['flag'].inverse_transform([int(original_row['flag'])])[0],
            'src_bytes': int(original_row['src_bytes']),
            'dst_bytes': int(original_row['dst_bytes']),
            'logged_in': int(original_row['logged_in']),
            'count': int(original_row['count']),
            'srv_count': int(original_row['srv_count']),
            'same_srv_rate': float(original_row['same_srv_rate']),
            'diff_srv_rate': float(original_row['diff_srv_rate']),
            'srv_diff_host_rate': float(original_row['srv_diff_host_rate']),
            'dst_host_count': int(original_row['dst_host_count']),
            'dst_host_srv_count': int(original_row['dst_host_srv_count']),
            'predicted_label': None,
            'real_label': self.label_enc.inverse_transform([int(original_row['label'])])[0],
            'normal_count': self.normal_count,
            'bad_count': self.bad_count,
            'bad_traffic_percentage': 0,
            'uuid': None
        }

# Column definitions for dataset
cols = [
    'duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes', 'land', 
    'wrong_fragment', 'urgent', 'hot', 'num_failed_logins', 'logged_in', 
    'num_compromised', 'root_shell', 'su_attempted', 'num_root', 
    'num_file_creations', 'num_shells', 'num_access_files', 'num_outbound_cmds', 
    'is_host_login', 'is_guest_login', 'count', 'srv_count', 'serror_rate', 
    'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 
    'diff_srv_rate', 'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count', 
    'dst_host_same_srv_rate', 'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate', 
    'dst_host_srv_diff_host_rate', 'dst_host_serror_rate', 
    'dst_host_srv_serror_rate', 'dst_host_rerror_rate', 
    'dst_host_srv_rerror_rate', 'label'
]
# For live data simulation, the dataset is loaded and preprocessed, we use type definitions to reduce memory usage and df type inference
df = pd.read_csv(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "kddcup_data_corrected.csv"),
    names=cols,
    dtype={
        'duration': 'int16', 'protocol_type': 'category', 'service': 'category',
        'flag': 'category','src_bytes': 'int32', 'dst_bytes': 'int32',
        'land': 'int8', 'wrong_fragment': 'int8', 'urgent': 'int8',
        'hot': 'int8', 'num_failed_logins': 'int8', 'logged_in': 'int8',
        'num_compromised': 'int8', 'root_shell': 'int8', 'su_attempted': 'int8',
        'num_root': 'int8', 'num_file_creations': 'int8', 'num_shells': 'int8',
        'num_access_files': 'int8', 'num_outbound_cmds': 'int8', 'is_host_login': 'int8',
        'is_guest_login': 'int8', 'count': 'int16', 'srv_count': 'int16', 'serror_rate': 'float64',
        'srv_serror_rate': 'float64', 'rerror_rate': 'float64', 'srv_rerror_rate': 'float64',
        'same_srv_rate': 'float64', 'diff_srv_rate': 'float64','srv_diff_host_rate': 'float64',
        'dst_host_count': 'int16', 'dst_host_srv_count': 'int16', 'dst_host_same_srv_rate': 'float64',
        'dst_host_diff_srv_rate': 'float64', 'dst_host_same_src_port_rate': 'float64', 'dst_host_srv_diff_host_rate': 'float64',
        'dst_host_serror_rate': 'float64', 'dst_host_srv_serror_rate': 'float64', 'dst_host_rerror_rate': 'float64',
        'dst_host_srv_rerror_rate': 'float64', 'label': 'category'
    },
    engine='c',
    low_memory=True
)
try:
    # Optimize label encoding and standardization
    le_encoders = {col: LabelEncoder() for col in ['protocol_type', 'service', 'flag']}  # Initialize label encoders for categorical columns (non-numeric)
    for col, le in le_encoders.items():
        df[col] = le.fit_transform(df[col]).astype('int8')  # Fit, transform, and downcast label encoder
except:
    print("Error during label transformation. Please check the dataset columns and types.")
    exit(1)

try:
    label_enc = LabelEncoder()  # Initialize label encoder for the target column
    df['label'] = label_enc.fit_transform(df['label']).astype('int8')  # Encode labels to integers and downcast
except:
    print("Error during label encoding. Please check the dataset columns and types.")
    exit(1)
# Copy data before standardization
try:
    df_copy = df.copy(deep=False)
except:
    print("Error during data copy. Please check the dataset columns and types.")
    exit(1)
    
# Vectorized standard scaling needed as preprocessing step for the neural network
try:
    scaler = StandardScaler() 
    df[df.columns[:-1]] = scaler.fit_transform(df[df.columns[:-1]]) # Fit and transform the standard scaler with all columns except the target column
except:
    print("Error during standard scaling. Please check the dataset columns and types.")
    exit(1)

# If new data is received, it can be standardized with the same scaler instance
# In this simulation, no new data is received

# Load neural network model trained_nn_model.pth
try:
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained_nn_model.pth")
    model = SimpleNN(input_size=df.shape[1] - 1, hidden_size=128, output_size=len(label_enc.classes_))

    checkpoint = torch.load(model_path, map_location=torch.device('cpu')) # Load the model checkpoint
    model.load_state_dict(checkpoint['model_state_dict']) # Load the model state dictionary which contains the model parameters
    model.eval()  # Set the model to evaluation mode
except:
    print("Error during model loading. Please check the model file.")
    exit(1)

# Create a global simulation object to manage the simulation state
# This object is used to start and stop the simulation for multiple users on different instances
simulations = []

def map_uuid_to_simulation(uuid: str) -> dict:
    """Maps the given UUID to the corresponding simulation object."""
    global simulations
    for simulation in simulations:
        if simulation[0] == uuid:
            return simulation[1]
    return None

def initialize_simulation(user_uuid: str) -> dict:
    """Initializes the simulation for the given user UUID."""
    global simulations
    simulation = {
        'status': threading.Event(),
        'data_simulator': DataSimulator(model, df, df_copy, label_enc, le_encoders, scaler),
        'thread': None
    }
    simulation['data_simulator'].uuid = user_uuid
    simulation['thread'] = threading.Thread(target=simulation['data_simulator'].
                                            simulate_incoming_data, 
                                            args=(simulation['status'],), daemon=True)
    simulations.append((user_uuid, simulation))
    return simulation

def get_dashboard_template() -> str:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates/dashboard.html')) as f:
        return f.read()

def decode_categorical_columns(df, le_encoders):
    for col, encoder in le_encoders.items():
        if col in df.columns:
            label_mapping = {i: label for i, label in enumerate(encoder.classes_)}
            df[col] = df[col].map(label_mapping)
    return df

def reorder_columns(df):
    cols = list(df.columns)
    if 'timestamp' in cols:
        cols.insert(0, cols.pop(cols.index('timestamp')))
    return df[cols]

def render_template_with_table(table_html, df_last_120):
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/datatable.html")) as f:
        template = f.read()
    return render_template_string(template, table_html=table_html, df_last_120=df_last_120)

def calculate_sha256(file_path):
    try:
        """Calculate the SHA-256 hash of a file."""
        sha256_hash = hashlib.sha256() 
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except:
        return "Error during SHA-256 calculation. Please check the file path."

def get_user_info(user_data_from_session: str) -> dict:
    return {
        'email': get_session_email(user_data_from_session),
        'role': get_session_role(user_data_from_session)
    }

def start_user_simulation(simulation: dict) -> None:
    if simulation and not simulation['thread'].is_alive():
        simulation['status'].clear()
        simulation['thread'] = threading.Thread(target=simulation['data_simulator'].
                                                simulate_incoming_data, 
                                                args=(simulation['status'],), daemon=True)
        simulation['thread'].start()
        socketio.emit('simulation_status', {'status': 'started'})

def stop_user_simulation(simulation: dict) -> None:
    if simulation and simulation['thread'].is_alive():
        simulation['status'].set()
        simulation['thread'].join()
        socketio.emit('simulation_status', {'status': 'stopped'})

def reset_user_data(simulation: dict) -> None:
    if simulation:
        simulation['data_simulator'].normal_count = 0
        simulation['data_simulator'].bad_count = 0
        simulation['data_simulator'].last_120_rows.clear()

@dashboard_routes.route('/user_info')
@role_required('user','admin')
def user_info() -> jsonify:
    try:
        user_data_from_session = request.cookies.get("logged_in")
        user_data = get_user_info(user_data_from_session)
        return jsonify(user_data)
    except:
        return "Error during user information retrieval. Please check the user information logic."

@socketio.on('start_simulation')
@role_required('user','admin')
def start_simulation() -> None:
    try:
        simulation = map_uuid_to_simulation(request.cookies.get('logged_in'))
        start_user_simulation(simulation)
    except:
        return "Error during simulation start. Please check the simulation logic."

@socketio.on('stop_simulation')
@role_required('user','admin')
def stop_simulation() -> None:
    try:
        simulation = map_uuid_to_simulation(request.cookies.get('logged_in'))
        stop_user_simulation(simulation)
    except:
        return "Error during simulation stop. Please check the simulation logic."


@socketio.on('reset_data')
@role_required('user','admin')
def reset_data() -> None:
    try:
        simulation = map_uuid_to_simulation(request.cookies.get('logged_in'))
        reset_user_data(simulation)
    except:
        return "Error during data reset. Please check the data reset logic."


@dashboard_routes.route('/received_data')
@role_required('user','admin')
def open_datatable():
    try:
        simulation = map_uuid_to_simulation(request.cookies.get('logged_in'))
        if simulation:
            data_simulator = simulation['data_simulator']
            last_120_rows = list(data_simulator.last_120_rows)
            if not last_120_rows:
                return "No data available. Start simulation first.", 500
            df_last_120 = pd.DataFrame(last_120_rows)
            df_last_120 = decode_categorical_columns(df_last_120, data_simulator.le_encoders)
            df_last_120 = reorder_columns(df_last_120)
            table_html = df_last_120.to_html(classes="table table-striped table-bordered", index=False)
            return render_template_with_table(table_html, df_last_120)
    except:
        return "Error during data retrieval. Please check the data retrieval logic."


@dashboard_routes.route('/model_evaluation')
@role_required('user','admin')
def model_evaluation():
    try:
        try:
            sha256_hash_calc = calculate_sha256(model_file_path) # Calculate the SHA-256 hash of the model file
        except:
            return "Error during calculating hash."
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates/modelinfo.html")) as f: # Open the model evaluation template
            template = f.read()
        return render_template_string(template, sha256_hash = sha256_hash_calc) # Return the model evaluation template with the SHA-256 hash
    except:
        return "Error during model evaluation. Please check the model evaluation logic."
    
@dashboard_routes.route('/download_model')
@role_required('user','admin')
def download_model():
    try:
        """Download the model file."""
        if os.path.exists(model_file_path):
            return send_file(model_file_path, as_attachment=True, download_name=os.path.basename(model_file_path)) # Send the model file as an attachment
        else:
            return "File not found", 500
    except:
        return "Error during model download. Please check the model download logic."
    
@dashboard_routes.route('/dashboard')
@role_required('user','admin')
def dashboard() -> str:
    try:
        user_uuid = request.cookies.get('logged_in')
        simulation = map_uuid_to_simulation(user_uuid)
        if simulation:
            return render_template_string(get_dashboard_template())
        else:
            initialize_simulation(user_uuid)
            return render_template_string(get_dashboard_template())
    except:
        return "Error during dashboard initialization. Please check the dashboard template."

if __name__ == '__main__': # Run the application if the script is executed directly (not imported)
    app = Flask(__name__)
    app.register_blueprint(dashboard_routes)
    socketio.init_app(app)
    socketio.run(app, host='0.0.0.0', port=5000)