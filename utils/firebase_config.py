import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Define collection names
TASKS_COLLECTION = "tasks"
USERS_COLLECTION = "users"
COUNTERS_COLLECTION = "counters"
NOTIFICATIONS_COLLECTION = "notifications"
COMPLIANCE_COLLECTION = "compliance_reports"

# Connect to Firebase
# We check if the app is already initialized to prevent errors on app rerun
if not firebase_admin._apps:
    try:
        # ---------------------------------------------------------
        # THIS IS THE FIX: Load from Streamlit Secrets, not a file
        # ---------------------------------------------------------
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Failed to initialize Firebase: {e}")

db = firestore.client()
