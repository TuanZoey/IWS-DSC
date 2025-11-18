# In file: utils/firebase_config.py

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# --- Define Collection Names (as used in your app.py) ---
USERS_COLLECTION = "users"
TASKS_COLLECTION = "tasks"
COMPLIANCE_COLLECTION = "compliance_reports"
NOTIFICATIONS_COLLECTION = "notifications"
COUNTERS_COLLECTION = "counters"

@st.cache_resource
def get_db():
    """
    Initializes and returns the Firebase Admin SDK app and Firestore client.
    Uses @st.cache_resource to connect only once.
    """
    try:
        # Check if app is already initialized
        if not firebase_admin._apps:
            # --- IMPORTANT ---
            # Change "service-account.json" to the name of your key file
            cred_path = "service-account.json" 
            
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase App Initialized.")
        
        # Return the firestore client
        return firestore.client()
        
    except FileNotFoundError:
        st.error(f"FATAL ERROR: Firebase service account key not found.")
        st.error(f"The file '{cred_path}' is missing.")
        st.stop()
    except Exception as e:
        st.error(f"Error initializing Firebase: {e}")
        st.stop()

# Initialize the database
try:
    db = get_db()
except Exception as e:
    db = None
    st.error(f"Failed to connect to Firestore: {e}")