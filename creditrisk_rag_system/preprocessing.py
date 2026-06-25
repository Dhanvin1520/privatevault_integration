import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split


def load_and_clean_data(filepath='data/loan_data.csv'):
    """Load the dataset and perform data cleaning.

    Steps: drop nulls, cap outliers at 99th percentile for age/income/experience,
    and binary-encode gender and previous defaults.
    """
    df = pd.read_csv(filepath)

    df = df.dropna()

    age_cap = df['person_age'].quantile(0.99)
    df = df[df['person_age'] <= age_cap]

    income_cap = df['person_income'].quantile(0.99)
    df = df[df['person_income'] <= income_cap]

    emp_cap = df['person_emp_exp'].quantile(0.99)
    df = df[df['person_emp_exp'] <= emp_cap]

    df['previous_loan_defaults_on_file'] = df['previous_loan_defaults_on_file'].map({'Yes': 1, 'No': 0})
    df['person_gender'] = df['person_gender'].map({'male': 1, 'female': 0})

    return df


def get_train_test_split(df):
    """Split the dataframe into 80/20 train-test sets."""
    X = df.drop(columns=['loan_status'])
    y = df['loan_status']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    return X_train, X_test, y_train, y_test


def encode_education(df):
    """Map education levels to ordinal values 0-4."""
    education_mapping = {
        'High School': 0,
        'Associate': 1,
        'Bachelor': 2,
        'Master': 3,
        'Doctorate': 4
    }

    df = df.copy()
    df['person_education'] = df['person_education'].map(education_mapping)
    return df


def encode_categories(df):
    """One-hot encode home ownership and loan intent columns."""
    df = pd.get_dummies(df, columns=['person_home_ownership', 'loan_intent'], drop_first=True)
    return df


def preprocess_features(df):
    """Apply all feature encoding: ordinal for education, one-hot for categoricals."""
    df = encode_education(df)
    df = encode_categories(df)
    return df
