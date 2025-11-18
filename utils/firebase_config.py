import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Define collection names
TASKS_COLLECTION = "tasks"
USERS_COLLECTION = "users"
COUNTERS_COLLECTION = "counters"
NOTIFICATIONS_COLLECTION = "notifications"
COMPLIANCE_COLLECTION = "compliance_reports"

# ---------------------------------------------------------
# ROBUST FIREBASE CONNECTION
# ---------------------------------------------------------
# Attempt to retrieve the existing app, or initialize a new one if it doesn't exist.
try:
    app = firebase_admin.get_app()
except ValueError:
    # The default app doesn't exist, so we initialize it.
    # NOTE: We do NOT use a try-except block here. If this fails, we WANT it to crash
    # so we can see the specific error message (e.g., "JSON parsing error").
    if "firebase" in st.secrets:
        key_dict = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key_dict)
        app = firebase_admin.initialize_app(cred)
    else:
        # Stop the app with a helpful message if secrets are missing
        st.error("Streamlit Secrets not found! Please configure '.streamlit/secrets.toml' or Cloud Secrets.")
        st.stop()

# Connect to the Firestore client
db = firestore.client()
