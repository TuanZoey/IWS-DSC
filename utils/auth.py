# In file: utils/auth.py

import streamlit as st
from .firebase_config import db, USERS_COLLECTION

def authenticate_user(username, password):
    """
    Authenticates a user against the Firestore database.
    
    WARNING: This checks plaintext passwords! 
    This is INSECURE and for demo purposes only.
    A real app MUST hash and salt passwords.
    """
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False, None
        
    try:
        user_ref = db.collection(USERS_COLLECTION).document(username)
        user_doc = user_ref.get()
        
        if not user_doc.exists:
            return False, None # User not found
            
        user_data = user_doc.to_dict()
        
        # Check password
        if user_data.get('password') == password:
            # Add username to data dict, as it's the document ID
            user_data['username'] = username
            return True, user_data
        else:
            return False, None # Incorrect password
            
    except Exception as e:
        st.error(f"Authentication error: {e}", icon="❌")
        return False, None

def initialize_sample_users():
    """
    Populates the Firestore database with the demo users
    listed on the login page.
    """
    if not db:
        st.error("Database connection not available.", icon="❌")
        return

    sample_users = {
        "admin": {
            "name": "Admin User",
            "email": "admin@facility.com",
            "password": "admin123",
            "role": "admin",
            "work_center": "All"
        },
        "supervisor": {
            "name": "Supervisor",
            "email": "supervisor@facility.com",
            "password": "super123",
            "role": "supervisor",
            "work_center": "All"
        },
        "electrical_user": {
            "name": "Elec Technician",
            "email": "elec@facility.com",
            "password": "electrical123",
            "role": "user",
            "work_center": "Electrical"
        },
        "mechanical_user": {
            "name": "Mech Technician",
            "email": "mech@facility.com",
            "password": "mechanical123",
            "role": "user",
            "work_center": "Mechanical"
        },
        "instrument_user": {
            "name": "Inst Technician",
            "email": "inst@facility.com",
            "password": "instrument123",
            "role": "user",
            "work_center": "Instrument"
        }
    }
    
    try:
        batch = db.batch()
        for username, data in sample_users.items():
            user_ref = db.collection(USERS_COLLECTION).document(username)
            batch.set(user_ref, data)
        
        batch.commit()
        st.success("Sample user accounts have been created!", icon="✅")
        
    except Exception as e:
        st.error(f"Error initializing sample users: {e}", icon="❌")