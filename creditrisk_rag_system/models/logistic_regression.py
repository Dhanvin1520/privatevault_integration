import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
import sys
sys.path.append('..')
from preprocessing import preprocess_features


def train(df):
    """Train a Logistic Regression model for loan default prediction.

    Uses StandardScaler for feature normalisation and class_weight='balanced'
    to handle class imbalance. Returns the trained model, scaler, feature names,
    and train/test splits.
    """
    df = preprocess_features(df)

    X = df.drop(columns=['loan_status'])
    y = df['loan_status']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    model = LogisticRegression(max_iter=1000, random_state=42, class_weight='balanced')
    model.fit(X_train_scaled, y_train)

    feature_names = list(X_train.columns)

    return model, scaler, feature_names, X_train, X_test, y_train, y_test
