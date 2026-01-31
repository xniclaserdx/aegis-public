import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import (accuracy_score, cohen_kappa_score, f1_score,
                             hamming_loss, matthews_corrcoef, precision_score,
                             recall_score)
from sklearn.model_selection import KFold
from sklearn.preprocessing import LabelEncoder, StandardScaler
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler
from tqdm import tqdm

# Load dataset with optimized memory usage
cols = ['duration', 'protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes', 'land', 'wrong_fragment', 'urgent', 
        'hot', 'num_failed_logins', 'logged_in', 'num_compromised', 'root_shell', 'su_attempted', 'num_root', 
        'num_file_creations', 'num_shells', 'num_access_files', 'num_outbound_cmds', 'is_host_login', 'is_guest_login', 
        'count', 'srv_count', 'serror_rate', 'srv_serror_rate', 'rerror_rate', 'srv_rerror_rate', 'same_srv_rate', 
        'diff_srv_rate', 'srv_diff_host_rate', 'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate', 
        'dst_host_diff_srv_rate', 'dst_host_same_src_port_rate', 'dst_host_srv_diff_host_rate', 'dst_host_serror_rate', 
        'dst_host_srv_serror_rate', 'dst_host_rerror_rate', 'dst_host_srv_rerror_rate', 'label']

df = pd.read_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "kddcup_data_corrected.csv"), names=cols) 

# Optimize label encoding and standardization
le_encoders = {col: LabelEncoder() for col in ['protocol_type', 'service', 'flag']} # Initialize label encoders for categorical columns (non-numeric)
for col, le in le_encoders.items():
    df[col] = le.fit_transform(df[col]) # Fit and transform the label encoder 

label_enc = LabelEncoder() # Initialize label encoder for the target column
df['label'] = label_enc.fit_transform(df['label']) # Encode labels to integers

# Vectorized standard scaling
scaler = StandardScaler()
df[df.columns[:-1]] = scaler.fit_transform(df[df.columns[:-1]]) # Fit and transform the standard scaler with all columns except the target column

# Dataset definition
class NetDataset(Dataset):
    def __init__(self, data):
        # Preload features and labels as tensors
        self.features = torch.tensor(data.drop('label', axis=1).values, dtype=torch.float32) # Features as float32 tensor
        self.labels = torch.tensor(data['label'].values, dtype=torch.long) # Labels as long tensor
    def __len__(self):
        return len(self.features)
    def __getitem__(self, idx):
        return self.features[idx], self.labels[idx] # Return features and labels as tensors


# Simple Neural Network
class SimpleNN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(SimpleNN, self).__init__() # Define the neural network architecture
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, output_size)
        self.relu = nn.ReLU()
        self.softmax = nn.LogSoftmax(dim=1)
    def forward(self, x):
        x = self.relu(self.fc1(x))
        x = self.relu(self.fc2(x))
        return self.softmax(self.fc3(x))
    def reset_parameters(self):
        for layer in self.children(): # Reset model parameters for each layer
            if hasattr(layer, 'reset_parameters'): # Check if the layer has a reset_parameters method
                layer.reset_parameters() # Reset the layer parameters

# Training function
def train(model, dl, loss_fn, opt, epochs, device):
    model.train()
    for epoch in range(epochs):
        running_loss = 0 # Initialize running loss to 0 for each epoch
        for data, target in tqdm(dl, desc=f"Epoch {epoch+1}/{epochs}"): # Iterate through the data loader
            data, target = data.to(device), target.to(device) # Move data and target to device (GPU or CPU)
            opt.zero_grad() # Clear the gradients
            output = model(data) # Forward pass
            loss = loss_fn(output, target)
            loss.backward() # Backward pass
            opt.step() # Update the weights
            running_loss += loss.item() # Accumulate the loss
        print(f"Epoch [{epoch+1}/{epochs}], Loss: {running_loss/len(dl):.4f}")

# Evaluation function
def evaluate(model, dl, device):
    model.eval()
    preds, labels = [], [] # Initialize empty lists for predictions and labels
    with torch.no_grad():
        for data, lbls in tqdm(dl, desc="Evaluating"):
            data, lbls = data.to(device), lbls.to(device) # Move data and labels to device
            outputs = model(data) # Get model predictions
            preds.extend(torch.argmax(outputs, 1).cpu().numpy()) # Append the predicted labels 
            labels.extend(lbls.cpu().numpy()) # Append the true labels
    
    # Performance Metrics
    precision = precision_score(labels, preds, average='weighted', zero_division=1)
    recall = recall_score(labels, preds, average='weighted', zero_division=1)
    f1 = f1_score(labels, preds, average='weighted', zero_division=1)
    accuracy = accuracy_score(labels, preds)
    macro_f1 = f1_score(labels, preds, average='macro', zero_division=1)
    micro_f1 = f1_score(labels, preds, average='micro', zero_division=1)
    mcc = matthews_corrcoef(labels, preds)
    kappa = cohen_kappa_score(labels, preds)
    hamming = hamming_loss(labels, preds)

    print(f"Weighted Precision: {precision:.4f}, Weighted Recall: {recall:.4f}, Weighted F1: {f1:.4f}")
    print(f"Accuracy: {accuracy:.4f}, Macro F1: {macro_f1:.4f}, Micro F1: {micro_f1:.4f}")
    print(f"MCC: {mcc:.4f}, Kappa: {kappa:.4f}, Hamming Loss: {hamming:.4f}")
    
    # Confusion Matrix with label names
    actual_labels = label_enc.inverse_transform(labels)
    predicted_labels = label_enc.inverse_transform(preds)
    confusion_matrix = pd.crosstab(pd.Series(actual_labels, name='Actual'), pd.Series(predicted_labels, name='Predicted'))
    plt.figure(figsize=(10, 7))
    sns.heatmap(confusion_matrix, annot=True, fmt='d', cmap='Blues')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.title('Confusion Matrix')
    plt.show()
    # Create a dictionary to map integer labels back to their original string labels
    int_to_label = {i: label for i, label in enumerate(label_enc.classes_)}
    print("Integer to Label Mapping:", int_to_label)

# Main Function
def main():
    input_size = df.shape[1] - 1
    hidden_size = 128
    output_size = len(label_enc.classes_)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu') # Check if GPU is available and set the device if available

    model = SimpleNN(input_size, hidden_size, output_size).to(device) # Initialize the model and move it to the device
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "trained_nn_model.pth") # Path to save the model

    # Check if model already exists
    if os.path.exists(model_path):
        print("Loading existing model.")
        checkpoint = torch.load(model_path)
        model.load_state_dict(checkpoint['model_state_dict'])
        evaluate(model, DataLoader(NetDataset(df), batch_size=32), device) # Evaluate the model on the entire dataset 
    else:
        print("Training a new model.")
        opt = optim.Adam(model.parameters(), lr=0.001)

        # Define custom weights for the classes
        print(df['label'].unique())  # Check all unique labels in the DataFrame
        print(label_enc.classes_)  # This will show the classes after encoding
        normal_class_index = label_enc.transform(["normal."])[0]
        class_weights = np.ones(len(label_enc.classes_))  # Start with all weights set to 1
        class_weights[normal_class_index] = 5.0  # Increase the weight for the "normal" to ensure bad traffic is not detected as normal (oder 5?)
        class_weights_tensor = torch.tensor(class_weights, dtype=torch.float32).to(device) # Move the class weights to the device

        # Update the loss function
        loss_fn = nn.CrossEntropyLoss(weight=class_weights_tensor) # Use the custom class weights in the loss function CrossEntropyLoss

        # K-Fold Cross-validation
        kfold = KFold(n_splits=5, shuffle=True, random_state=42) # Initialize KFold with 5 splits and random seed
        for fold, (train_idx, val_idx) in enumerate(kfold.split(df)): # Iterate through each fold and split the data
            print(f'Fold {fold + 1}/{kfold.n_splits}') 
            train_df, val_df = df.iloc[train_idx], df.iloc[val_idx] # Get training and validation data

            # Create a sampler based on class imbalance
            class_sample_count = np.bincount(train_df['label']) # Count the number of samples in each class
            weights = 1. / class_sample_count[train_df['label']] # Calculate the weights based on the class distribution
            sampler = WeightedRandomSampler(weights=weights, num_samples=len(weights), replacement=True) # Create a WeightedRandomSampler to handle class imbalance

            train_dl = DataLoader(NetDataset(train_df), batch_size=32, sampler=sampler) # Create DataLoader for training data with the sampler
            val_dl = DataLoader(NetDataset(val_df), batch_size=32) # Create DataLoader for validation data

            model.reset_parameters()  # Reset model parameters
            train(model, train_dl, loss_fn, opt, epochs=5, device=device) # Train the model with the custom loss function for 5 epochs
        evaluate(model, val_dl, device) # Evaluate the model on the validation set
        torch.save({'model_state_dict': model.state_dict()}, model_path) # Save the model after training to model_path

if __name__ == "__main__":
    main()
