import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier
import sys
sys.path.append('..')
from preprocessing import preprocess_features


def train(df):
    """Train an XGBoost classifier for loan default prediction.

    Uses gradient boosting with 200 estimators, learning_rate=0.05,
    and scale_pos_weight to handle class imbalance. Subsample and
    colsample_bytree are set to 0.8 for regularisation.
    Returns the trained model, feature names, and train/test splits.
    """
    df = preprocess_features(df)

    X = df.drop(columns=['loan_status'])
    y = df['loan_status']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    scale_pos_weight = len(y_train[y_train == 0]) / len(y_train[y_train == 1])

    model = XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )
    model.fit(X_train, y_train)

    feature_names = list(X_train.columns)

    return model, feature_names, X_train, X_test, y_train, y_test
