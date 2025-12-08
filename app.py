import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from utils.firebase_config import db, USERS_COLLECTION, TASKS_COLLECTION
from utils.auth import authenticate_user, initialize_sample_users

# Imports for PDF Generation 
from fpdf import FPDF

# Imports WO Counter Findings
from firebase_admin import firestore 
import re
from collections import Counter


# Firebase_collection
COMPLIANCE_COLLECTION = "compliance_reports"
NOTIFICATIONS_COLLECTION = "notifications"
COUNTERS_COLLECTION = "counters" 



# Page 
st.set_page_config(
    page_title="IWA-DCS",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Location
LOCATION_MAP = {
    'TGAST': 'Onshore',
    'TCOT': 'Onshore',
    'Tiong': 'Offshore',
    'Angsi': 'Offshore'
}
ALL_LOCATIONS = list(LOCATION_MAP.keys())


# Duration based on worktype
ELECTRICAL_DURATIONS = {
    "Preventive Maintenance": 4, 
    "Corrective Maintenance": 8, 
    "Installation": 12, 
    "Troubleshooting": 6,
    "Default": 4
}
MECHANICAL_DURATIONS = {
    "Preventive Maintenance": 6, 
    "Corrective Maintenance": 10, 
    "Overhaul": 24, 
    "Alignment": 4, 
    "Lubrication": 2, 
    "Inspection": 2,
    "Default": 6
}
INSTRUMENT_DURATIONS = {
    "Calibration": 3, 
    "Troubleshooting": 5, 
    "Installation": 8, 
    "Configuration": 2, 
    "Repair": 6, 
    "Testing": 4,
    "Default": 3
}

# lists for form selectboxes
ELEC_WORK_TYPES = list(ELECTRICAL_DURATIONS.keys())
MECH_WORK_TYPES = list(MECHANICAL_DURATIONS.keys())
INST_WORK_TYPES = list(INSTRUMENT_DURATIONS.keys())



# Standard Safety Checks
STANDARD_SAFETY_CHECKS = [
    "Permit-to-Work (PTW) Required", 
    "Lock-out / Tag-out (LOTO) Required", 
    "Job Safety Analysis (JSA) Completed", 
    "Toolbox Talk Conducted", 
    "Correct PPE (Gloves, Goggles, etc.) Verified", 
    "Area Barricaded",
    "Confined Space Entry Permit",
    "Gas Test Conducted"
]

# Stop Words for Findings Analysis
STOP_WORDS = set([
    'a', 'an', 'and', 'the', 'in', 'is', 'it', 'of', 'for', 'on', 'with', 'was', 'to', 
    'as', 'at', 'by', 'but', 'or', 'be', 'not', 'no', 'na', 'n/a', 'leaking', 'found',
    'observed', 'requires', 'required', 'needs', 'due', 'level', 'high', 'low', 'unit',
    'equipment', 'work', 'task', 'see', 'check', 'checked', 'also', 'has', 'had', 'per',
    'need', 'replace', 'repair', 'broken', 'faulty', 'damage', 'damaged'
])

# Dynamic Sheet
CHECKLIST_DEFINITIONS = {
    'Electrical': {
        'Motor': [
            "Inspect enclosure for damage or water ingress",
            "Check for signs of overheating (discoloration, smell)",
            "Verify all terminal connections are tight",
            "Check that all labels are clear and correct",
            "Test grounding (Megger test)",
            "Verify cable insulation is in good condition",
            "Check cooling fans are operational",
            "Check bearing condition (noise/vibration)",
            "Test functional operation (Start/Stop)"
        ],
        'Switchgear': [
            "Inspect enclosure for dust/damage",
            "Check busbar connections for tightness (torque)",
            "Verify all indicators (lights) are functional",
            "Test circuit breaker trip mechanism",
            "Check relay settings against a drawing",
            "Inspect grounding connections",
            "Verify control voltage levels"
        ],
        'Default': [
            "Inspect for general damage or corrosion",
            "Verify all connections are secure",
            "Check for signs of overheating",
            "Verify correct labeling",
            "Test functional operation"
        ]
    },
    'Mechanical': {
        'Pump': [
            "Check for unusual noise or vibration",
            "Inspect for leaks (oil, process fluid) at seals",
            "Check bearing temperatures",
            "Verify lubrication levels and condition",
            "Inspect couplings and guards for alignment/condition",
            "Check mounting bolts for tightness",
            "Verify suction/discharge pressure gauges are reading correctly"
        ],
        'Compressor': [
            "Check for unusual noise or vibration",
            "Inspect for air/gas/oil leaks",
            "Check bearing temperatures",
            "Verify lubrication oil level and pressure",
            "Check and clean inlet filters",
            "Drain any water from air receivers/separators",
            "Verify correct operating pressure and temperature",
            "Test safety relief valve (if applicable)"
        ],
        'Default': [
            "Check for unusual noise or vibration",
            "Inspect for leaks (oil, water, process fluid)",
            "Check bearing temperatures (if applicable)",
            "Verify lubrication levels and condition",
            "Inspect guards for condition",
            "Check for corrosion or external damage"
        ]
    },
    'Instrument': {
        'Control Valve': [
            "Tag Number - Available/Visible/Readable/Correct",
            "Manufacturer's Name Plate (Actuator and Valve Body) - Available/Visible/Readable",
            "Valve Body - No visible damage",
            "Valve Body - No sign of corrosion",
            "Valve Body - Painting in good condition",
            "Valve Body - Body insulated (If applicable)",
            "Valve Body - No abnormal noise",
            "Valve Body - No pipe vibration around the valve",
            "Valve Actuator - No Visible damage",
            "Valve Actuator - No sign of corrosion",
            "Valve Actuator - Painting in good condition",
            "Valve Actuator - No actuator leak observed (Perform actuator leak test)",
            "Valve Actuator - The Position mechanical indicator is in good condition",
            "Air Filter regulator - In good condition & No Corrosion",
            "Air Filter regulator - No leakage",
            "Air Filter regulator - Pressure gauge in good condition",
            "Air Filter regulator - Air pressure is set to relevant pressure",
            "Perform stroke check (Open/Close)"
        ],
        'Transmitter': [
            "Tag Number - Available/Visible/Readable/Correct",
            "Inspect enclosure for damage/water ingress",
            "Check cabling and conduit for damage",
            "Verify process isolation valves are accessible and correct (e.g., 3-valve manifold)",
            "Check for any process leaks at connections",
            "Verify local display is readable (if applicable)",
            "Compare local reading to DCS/system reading",
            "Check air supply (if pneumatic)",
            "Perform Zero/Span check (as required)"
        ],
        'Default': [
            "Tag Number - Available/Visible/Readable/Correct",
            "Inspect enclosure for damage/water ingress",
            "Check cabling and conduit for damage",
            "Verify local display is readable (if applicable)",
            "Compare local reading to DCS/system reading",
            "Check for general corrosion or damage"
        ]
    }
}


ELEC_EQUIPMENT_TYPES = list(CHECKLIST_DEFINITIONS['Electrical'].keys())
MECH_EQUIPMENT_TYPES = list(CHECKLIST_DEFINITIONS['Mechanical'].keys())
INST_EQUIPMENT_TYPES = list(CHECKLIST_DEFINITIONS['Instrument'].keys())



# Initialize session state
def initialize_session_state():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "login"

# Firebase Data Functions
def get_next_work_order_number():
    """
    Atomically increments and returns a new work order number.
    e.g., WO-00001
    """
    if not db:
        st.error("Database connection not available.", icon="❌")
        return None
    
    counter_ref = db.collection(COUNTERS_COLLECTION).document("work_order_counter")
    
    @firestore.transactional
    def update_in_transaction(transaction, doc_ref):
        doc = doc_ref.get(transaction=transaction)
        if not doc.exists:
            new_val = 1
            transaction.set(doc_ref, {'current_number': new_val})
        else:
            new_val = doc.to_dict()['current_number'] + 1
            transaction.update(doc_ref, {'current_number': new_val})
        return new_val

    try:
        transaction = db.transaction()
        next_number = update_in_transaction(transaction, counter_ref)
        if next_number:
            return f"WO-{next_number:05d}"
        else:
            return None
    except Exception as e:
        st.error(f"Error generating work order number: {e}", icon="❌")
        return None



def get_all_tasks():
    """Get all tasks from Firebase"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return []
    try:
        tasks_ref = db.collection(TASKS_COLLECTION)
        tasks = tasks_ref.stream()
        return [{'id': task.id, **task.to_dict()} for task in tasks]
    except Exception as e:
        st.error(f"Error fetching tasks: {e}", icon="❌")
        return []

def get_tasks_by_filters(filters=None):
    """Get tasks with filters"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return []
    try:
        tasks_ref = db.collection(TASKS_COLLECTION)
        
        query = tasks_ref
        
        # Firestore query filters
        if filters:
            if 'work_center' in filters and filters['work_center']:
                query = query.where('work_center', '==', filters['work_center'])
            
            if 'status' in filters and filters['status']:
                if isinstance(filters['status'], list):
                    if len(filters['status']) > 0 and len(filters['status']) <= 10:
                        query = query.where('status', 'in', filters['status'])
                    elif len(filters['status']) == 0:
                        return []
                else:
                    query = query.where('status', '==', filters['status'])
        
        tasks = query.stream()
        task_list = []
        for task in tasks:
            task_data = task.to_dict()
            task_data['id'] = task.id
            task_list.append(task_data)
        #Python filter
        if filters:
            if 'location_type' in filters and filters['location_type']:
                if isinstance(filters['location_type'], list):
                    task_list = [t for t in task_list if t.get('location_type') in filters['location_type']]
                else:
                    task_list = [t for t in task_list if t.get('location_type') == filters['location_type']]
            
            if 'specific_location' in filters and filters['specific_location']:
                task_list = [t for t in task_list if t.get('specific_location') == filters['specific_location']]
            
            if 'username' in filters and filters['username']:
                task_list = [t for t in task_list if t.get('submitted_by') == filters['username']]
            
            if 'status' in filters and isinstance(filters['status'], list):
                task_list = [t for t in task_list if t.get('status') in filters['status']]

        return task_list
    except Exception as e:
        st.error(f"Error fetching tasks: {e}", icon="❌")
        return []

# Add WO Numbe
def add_task(task_data):
    """
    Add task to Firebase with all metadata (WO Number, User, Timestamp).
    'task_data' now only contains data from the form.
    """
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False, None
    try:
        # 1. Get new Work Order Number
        wo_number = get_next_work_order_number()
        if not wo_number:
            st.error("Failed to generate Work Order Number.", icon="❌")
            return False, None
        
        #Add data to the task_data
        task_data['work_order_number'] = wo_number
        task_data['submitted_by'] = st.session_state.user_data.get('username', 'unknown')
        task_data['submitted_by_name'] = st.session_state.user_data['name']
        task_data['submission_date'] = datetime.now().isoformat()
        task_data['status'] = 'pending'
        
        # Save to Firebase
        tasks_ref = db.collection(TASKS_COLLECTION)
        tasks_ref.add(task_data)
        
        # Return success and the new WO number
        return True, wo_number 
    except Exception as e:
        st.error(f"Error adding task: {e}", icon="❌")
        return False, None


def update_task_status(task_id, status, feedback="", reviewed_by=""):
    """Update task status in Firebase and create notification if rejected"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False
    try:
        task_ref = db.collection(TASKS_COLLECTION).document(task_id)
        
        #designated person submit form
        task_doc = task_ref.get()
        if not task_doc.exists:
            st.error("Task not found.", icon="❌")
            return False
        task_data = task_doc.to_dict()

        # Prepare update data
        update_data = {
            'status': status,
            'feedback': feedback,
            'reviewed_by': reviewed_by,
            'review_date': datetime.now().isoformat()
        }
        
        # Update the task
        task_ref.update(update_data)
        
        # notification if the task is rejected 
        if status == 'rejected' and feedback:
            submitted_by_username = task_data.get('submitted_by')
            if submitted_by_username:
                # Create a notification for the user who submitted the task
                notif_ref = db.collection(NOTIFICATIONS_COLLECTION)
                notif_data = {
                    'username': submitted_by_username,
                    'message': f"Work Order '{task_data.get('work_order_number', task_id)}' was rejected. Reason: {feedback}",
                    'read': False,
                    'timestamp': datetime.now().isoformat(),
                    'task_id': task_id
                }
                notif_ref.add(notif_data)
        
        return True
    except Exception as e:
        st.error(f"Error updating task: {e}", icon="❌")
        return False


def get_unread_notifications(username):
    """Get all unread notifications for a user"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return []
    try:
        notif_ref = db.collection(NOTIFICATIONS_COLLECTION)
        
        query = notif_ref.where('username', '==', username).where('read', '==', False).order_by('timestamp', direction=firestore.Query.DESCENDING)
        notifications = query.stream()
        return [{'id': notif.id, **notif.to_dict()} for notif in notifications]
    except Exception as e:
        st.error(f"Error fetching notifications: {e}", icon="❌")
        return []

def mark_notification_read(notification_id):
    """Mark a notification as read"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False
    try:
        notif_ref = db.collection(NOTIFICATIONS_COLLECTION).document(notification_id)
        notif_ref.update({'read': True})
        return True
    except Exception as e:
        st.error(f"Error dismissing notification: {e}", icon="❌")
        return False

def save_compliance_report(report_data):
    """Save a new compliance report to Firebase"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False
    try:
        db.collection(COMPLIANCE_COLLECTION).add(report_data)
        return True
    except Exception as e:
        st.error(f"Error saving compliance report: {e}", icon="❌")
        return False

# compliance location
def get_compliance_reports(location):
    """Get all compliance reports for a specific location"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return []
    try:
        reports_ref = db.collection(COMPLIANCE_COLLECTION)
        
        query = reports_ref.where('location', '==', location).order_by('report_date', direction=firestore.Query.DESCENDING)
        reports = query.stream()
        return [{'id': report.id, **report.to_dict()} for report in reports]
    except Exception as e:
        st.error(f"Error fetching compliance reports: {e}", icon="❌")
        return []

# PDF Generation Functions 

class PDF(FPDF):
    """Custom PDF class with header and footer"""
    def header(self):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, 'Work Order Maintenance Report', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        page_num = f'Page {self.page_no()}/{{nb}}'
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self.cell(0, 10, page_num, 0, 0, 'L')
        self.cell(0, 10, f'Report Generated: {gen_time}', 0, 0, 'R')

def safe_text(text):
    """Helper to clean text for FPDF latin-1 encoding"""
    if text is None:
        return "N/A"
    return str(text).encode('latin-1', 'replace').decode('latin-1')

def generate_task_pdf(task_data):
    """Generates a dynamic PDF report for a given task and returns it as bytes"""
    
    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.add_page()
    pdf.set_font('Arial', '', 10)
    
    line_height = 7 # Define a standard line height
    
    #Helper function for metadata rows 
    def add_dual_row(l1, v1, l2, v2):
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, line_height, safe_text(l1), 1, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(55, line_height, safe_text(v1), 1, 0)
        
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, line_height, safe_text(l2), 1, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(55, line_height, safe_text(v2), 1, 1) # ln=1 for new line
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '1. Work Order Details', 0, 1, 'L')
    
    # Get dynamic names
    equip_name = task_data.get('equipment_name', task_data.get('instrument_name', 'N/A'))
    equip_type = task_data.get('equipment_type', task_data.get('instrument_type', 'N/A'))
    
    add_dual_row("Work Order #:", task_data.get('work_order_number'), "Status:", task_data.get('status', 'N/A').title())
    add_dual_row("Submitted By:", task_data.get('submitted_by_name'), "Submission Date:", task_data.get('submission_date', 'N/A')[:10])
    add_dual_row("Work Center:", task_data.get('work_center'), "Priority:", task_data.get('priority'))
    add_dual_row("Location Type:", task_data.get('location_type'), "Location:", task_data.get('specific_location'))
    add_dual_row("Area/Unit:", task_data.get('area'), "Est. Duration (h):", task_data.get('estimated_duration'))
    add_dual_row("Equipment Tag:", equip_name, "Equipment Type:", equip_type)
    
    # Single row for Work Type
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(40, line_height, safe_text("Work Type:"), 1, 0)
    pdf.set_font('Arial', '', 10)
    pdf.cell(150, line_height, safe_text(task_data.get('work_type')), 1, 1)

    # Findings ---
    pdf.ln(5) # Add space
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '2. Overall Findings / Summary', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    pdf.multi_cell(190, line_height - 2, safe_text(task_data.get('overall_findings', 'N/A')), 1, 1)
    
    #  Safety ---
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '3. Safety Checks Performed', 0, 1, 'L')
    pdf.set_font('Arial', '', 10)
    
    safety_checks = task_data.get('safety_checks', [])
    if not safety_checks:
        pdf.cell(190, line_height, "No safety checks recorded.", 1, 1)
    else:
        safety_text = ""
        for check in safety_checks:
            safety_text += f"- {safe_text(check)}\n"
        pdf.multi_cell(190, line_height - 2, safety_text, 1, 1)

    # Checklist ---
    pdf.ln(5)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, '4. PPM Checklist Results', 0, 1, 'L')
    
    # Table Header
    col_width_task = 110
    col_width_status = 25
    col_width_remarks = 55
    
    pdf.set_font('Arial', 'B', 10)
    pdf.cell(col_width_task, line_height, 'Task Description', 1, 0, 'C')
    pdf.cell(col_width_status, line_height, 'Status', 1, 0, 'C')
    pdf.cell(col_width_remarks, line_height, 'Remarks', 1, 1, 'C')
    
    pdf.set_font('Arial', '', 9)
    checklist_data = task_data.get('checklist_data', [])
    
    if not checklist_data:
           pdf.cell(190, line_height, "No checklist data found.", 1, 1, 'C')
    else:
        for item in checklist_data:
            task_desc = safe_text(item.get('task', 'N/A'))
            status = safe_text(item.get('status', 'N/A'))
            remarks = safe_text(item.get('remarks', 'N/A'))
            
            # Get Y position before drawing row
            y_start = pdf.get_y()
            
            # Cell Task
            pdf.multi_cell(col_width_task, line_height - 2, task_desc, 1, 'L')
            y1 = pdf.get_y() # Get Y after drawing
            
            # Reset X,Y for Cell 2
            pdf.set_xy(pdf.get_x() + col_width_task, y_start)
            
            # Cell Status
            pdf.multi_cell(col_width_status, line_height - 2, status, 1, 'C')
            y2 = pdf.get_y() # Get Y after drawing
            
            # Reset X,Y for Cell 3
            pdf.set_xy(pdf.get_x() + col_width_task + col_width_status, y_start)
            
            # Cell Remarks
            pdf.multi_cell(col_width_remarks, line_height - 2, remarks, 1, 'L')
            y3 = pdf.get_y() # Get Y after drawing

            # Set cursor to the bottom of the tallest cell 
            max_y = max(y1, y2, y3)
            pdf.set_y(max_y)

    # Output the PDF as bytes
    return pdf.output().encode('latin-1')


# User Profile Functions 
def update_user_profile_details(username, name, email):
    """Update user's name and email in Firebase"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False
    try:
        user_ref = db.collection(USERS_COLLECTION).document(username)
        user_ref.update({
            'name': name,
            'email': email
        })
        return True
    except Exception as e:
        st.error(f"Error updating profile: {e}", icon="❌")
        return False

def update_user_password(username, old_password, new_password):
    """Update user's password in Firebase after verifying the old one"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False, "Database connection not available."
    try:
        user_ref = db.collection(USERS_COLLECTION).document(username)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return False, "User not found."
            
        user_data = user_doc.to_dict()
        
        # comparing plaintext passwords.
        if user_data.get('password') == old_password:
            user_ref.update({'password': new_password})
            return True, "Password updated successfully!"
        else:
            return False, "Incorrect current password."
            
    except Exception as e:
        st.error(f"Error updating password: {e}", icon="❌")
        return False, f"An error occurred: {e}"

def delete_user_from_db(username):
    """Delete a user document from Firebase"""
    if not db:
        st.error("Database connection not available.", icon="❌")
        return False
    try:
        db.collection(USERS_COLLECTION).document(username).delete()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}", icon="❌")
        return False

# KPI Calculation Functions
def calculate_kpis(tasks):
    """Calculate key performance indicators"""
    if not tasks:
        return {
            'total_tasks': 0,
            'completed_tasks': 0,
            'approval_rate': 0,
            'avg_completion_time': 0,
            'work_center_performance': {},
            'location_performance': {},
            'location_type_performance': {}
        }
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t['status'] in ['approved', 'rejected']])
    approved_tasks = len([t for t in tasks if t['status'] == 'approved'])
    
    approval_rate = (approved_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
    

    #Avg Completion Time Calculation
    completion_times = []
    for task in tasks:
        if task['status'] in ['approved', 'rejected']:
            duration = task.get('estimated_duration')
            if isinstance(duration, (int, float)):
                completion_times.append(duration)
                
    avg_completion_time = np.mean(completion_times) if completion_times else 0
    
    # Work center performance
    work_centers = set(task['work_center'] for task in tasks)
    work_center_performance = {}
    for wc in work_centers:
        wc_tasks = [t for t in tasks if t['work_center'] == wc]
        wc_completed = len([t for t in wc_tasks if t['status'] in ['approved', 'rejected']])
        wc_approved = len([t for t in wc_tasks if t['status'] == 'approved'])
        wc_approval_rate = (wc_approved / wc_completed * 100) if wc_completed > 0 else 0
        work_center_performance[wc] = wc_approval_rate
    
    # Location performance
    locations = set(task.get('specific_location', 'Unknown') for task in tasks)
    location_performance = {}
    for loc in locations:
        loc_tasks = [t for t in tasks if t.get('specific_location') == loc]
        loc_completed = len([t for t in loc_tasks if t['status'] in ['approved', 'rejected']])
        loc_approved = len([t for t in loc_tasks if t['status'] == 'approved'])
        loc_approval_rate = (loc_approved / loc_completed * 100) if loc_completed > 0 else 0
        location_performance[loc] = loc_approval_rate
    
    # Location type performance
    location_types = set(task.get('location_type', 'Unknown') for task in tasks)
    location_type_performance = {}
    for loc_type in location_types:
        type_tasks = [t for t in tasks if t.get('location_type') == loc_type]
        type_completed = len([t for t in type_tasks if t['status'] in ['approved', 'rejected']])
        type_approved = len([t for t in type_tasks if t['status'] == 'approved'])
        type_approval_rate = (type_approved / type_completed * 100) if type_completed > 0 else 0
        location_type_performance[loc_type] = type_approval_rate
    
    return {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'approval_rate': approval_rate,
        'avg_completion_time': avg_completion_time,
        'work_center_performance': work_center_performance,
        'location_performance': location_performance,
        'location_type_performance': location_type_performance
    }

def predict_kpi_trend(tasks, days=30):
    """Predict KPI trends for the next period"""
    historical_data = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        # Filter tasks submitted on this day
        day_tasks = [
            t for t in tasks 
            if 'submission_date' in t and t['submission_date'].startswith(date_str)
        ]
        
        if day_tasks:
            day_kpis = calculate_kpis(day_tasks)
            historical_data.append({
                'date': current_date,
                'approval_rate': day_kpis['approval_rate'],
                'completion_rate': (day_kpis['completed_tasks'] / day_kpis['total_tasks'] * 100) if day_kpis['total_tasks'] > 0 else 0
            })
        
        current_date += timedelta(days=1)
    
    # Simple prediction
    if len(historical_data) >= 2:
        approval_rates = [d['approval_rate'] for d in historical_data]
        current_rate = approval_rates[-1] if approval_rates else 0
        
        # Use simple moving average or trend
        x = np.arange(len(approval_rates))
        y = np.array(approval_rates)
        
        try:
            # Fit a linear trend
            trend_poly = np.polyfit(x, y, 1)
            trend = trend_poly[0] # The slope
        except np.linalg.LinAlgError:
            trend = 0 
            # Handle singular matrix error if data is flat

        # Predict 7 days out
        predicted_rate = current_rate + (trend * 7) 
        predicted_rate = max(0, min(100, predicted_rate))
        
        # Achievement probability
        recent_rates = approval_rates[-7:] if len(approval_rates) >= 7 else approval_rates
        above_target = sum(1 for rate in recent_rates if rate >= 80)
        achievement_probability = (above_target / len(recent_rates) * 100) if recent_rates else 0
        
        return {
            'current_rate': current_rate,
            'predicted_rate': predicted_rate,
            'trend': trend,
            'achievement_probability': achievement_probability,
            'historical_data': historical_data
        }
    
    return {
        'current_rate': 0,
        'predicted_rate': 0,
        'trend': 0,
        'achievement_probability': 0,
        'historical_data': []
    }

# Helper Function for Findings Analysis 
def analyze_findings_text(findings_list):
    """Processes a list of finding strings and returns a Counter of common words."""
    all_text = ' '.join(findings_list).lower()
    
    # Remove punctuation
    all_text = re.sub(r'[^\w\s]', '', all_text)
    
    words = all_text.split()
    
    # Filter out stop words and short words
    filtered_words = [
        word for word in words 
        if word not in STOP_WORDS and len(word) > 3
    ]
    
    return Counter(filtered_words).most_common(20)


# RENDER CHECKLIST ---
def render_checklist(checklist_definitions, work_center_key):
    """
    Renders a checklist with PASS/FAIL/NA and Remarks for each item.
    Returns a list of dictionaries with the results.
    """
    st.subheader("📋 PPM Checklist")
    st.markdown("For each item, select **PASS**, **FAIL**, or **NA** (Not Applicable).")
    st.markdown("---")
    
    checklist_data = []
    
    # Use columns for a cleaner layout
    col_header_1, col_header_2, col_header_3 = st.columns([3, 2, 3])
    with col_header_1:
        st.markdown("**Task Description**")
    with col_header_2:
        st.markdown("**Status (PASS/FAIL/NA)**")
    with col_header_3:
        st.markdown("**Remarks**")

    # Create a container for the checklist items
    with st.container(border=True):
        if not checklist_definitions:
            st.warning("No checklist defined for this equipment type.")
            return []
            
        for i, item_description in enumerate(checklist_definitions):
            col1, col2, col3 = st.columns([3, 2, 3])
            
            with col1:
                st.markdown(f"{item_description}")
            
            with col2:
                status_key = f"{work_center_key}_status_{i}"
                status = st.radio(
                    "Status", 
                    ["PASS", "FAIL", "NA"], 
                    key=status_key, 
                    horizontal=True, 
                    label_visibility="collapsed"
                )
            
            with col3:
                remarks_key = f"{work_center_key}_remarks_{i}"
                remarks = st.text_input(
                    "Remarks", 
                    key=remarks_key, 
                    label_visibility="collapsed", 
                    placeholder="Add remarks if FAIL or NA..."
                )
                
            checklist_data.append({
                "task": item_description, 
                "status": status, 
                "remarks": remarks
            })
            
            if i < len(checklist_definitions) - 1:
                st.markdown("---")

    return checklist_data


#  electrical_form=
def electrical_form():
    st.subheader("🔌 Electrical Work Order (PPM)")
    selected_equipment = st.selectbox(
        "Select Equipment Type*", 
        ELEC_EQUIPMENT_TYPES, 
        key="elec_equip_type",
        help="Select an equipment type to load the correct checklist below."
    )

    
    with st.form("electrical_form", clear_on_submit=True):
        
        st.subheader("1. Work Order Details")
        
        col1, col2 = st.columns(2)
        with col1:
            specific_location = st.selectbox("Specific Location*", ALL_LOCATIONS, key="elec_loc")
            area = st.text_input("Area/Unit*", key="elec_area")
            priority = st.selectbox("Priority*", ["Low", "Medium", "High"], key="elec_priority")
            
            # Dynamic Equipment Selection 
            # disabled text input to show the user what they selected
            st.text_input("Selected Equipment Type", value=selected_equipment, disabled=True)
            
        with col2:
            location_type = LOCATION_MAP[specific_location]
            st.text_input("Location Type", value=location_type, disabled=True, help="Auto-detected based on Specific Location.")
            equipment_tag = st.text_input("Equipment Name/Tag*", key="elec_equip_tag", placeholder="e.g., MTR-101A")

            #  Auto-Duration 
            work_type = st.selectbox("Select Work Type*", ELEC_WORK_TYPES, key="elec_work_type")
            estimated_duration = ELECTRICAL_DURATIONS.get(work_type, ELECTRICAL_DURATIONS["Default"])
            st.text_input("Estimated Duration (hours)", value=f"{estimated_duration}", disabled=True, help="Auto-calculated based on Work Type.")
          
            
        
        # Call Dynamic Checklist Renderer 
        st.markdown("---")
        checklist_to_render = CHECKLIST_DEFINITIONS['Electrical'].get(selected_equipment, CHECKLIST_DEFINITIONS['Electrical']['Default'])
        checklist_results = render_checklist(checklist_to_render, "elec")
     
        
        
        #  Overall Findings Safety 
        st.markdown("---")
        st.subheader("3. Summary & Safety")
        
        overall_findings = st.text_area("Overall Findings / Summary", 
            placeholder="Provide a general summary of the work, or detail any major findings...", height=100, key="elec_findings")
        
        safety_checks_selected = st.multiselect("Safety Checks Performed", 
            options=STANDARD_SAFETY_CHECKS, key="elec_safety")
        
        st.markdown("---")
        submitted = st.form_submit_button("Submit Electrical Work Order")
        
        if submitted:
            # validation
            if all([specific_location, equipment_tag, area, selected_equipment, work_type]):
                task_data = {
                    'work_center': 'Electrical',
                    'location_type': location_type,
                    'specific_location': specific_location,
                    'area': area,
                    'equipment_name': equipment_tag,      # The specific tag
                    'equipment_type': selected_equipment, # The category (Motor, etc)
                    'work_type': work_type,               # The work type (PM, CM, etc)
                    'priority': priority,
                    'estimated_duration': estimated_duration, # The auto-calculated duration
                    'checklist_data': checklist_results,
                    'overall_findings': overall_findings,
                    'safety_checks': safety_checks_selected,
                }
                
                success, wo_number = add_task(task_data) 
                
                if success:
                    st.success(f"Work Order {wo_number} submitted successfully!", icon="✅")
                    st.balloons()
                else:
                    st.error("Error submitting work order", icon="❌")
            else:
                st.error("Please fill in all required fields (*): Location, Area, Equipment Name/Tag, and Work Type.", icon="❌")


# mechanical_form 
def mechanical_form():
    st.subheader("⚙️ Mechanical Work Order (PPM)")
    

    selected_equipment = st.selectbox(
        "Select Equipment Type*", 
        MECH_EQUIPMENT_TYPES, 
        key="mech_equip_type",
        help="Select an equipment type to load the correct checklist below."
    )

    
    with st.form("mechanical_form", clear_on_submit=True):
        
        st.subheader("1. Work Order Details")
        
 
        col1, col2 = st.columns(2)
        with col1:
            specific_location = st.selectbox("Specific Location*", ALL_LOCATIONS, key="mech_loc")
            area = st.text_input("Area/Unit*", key="mech_area")
            priority = st.selectbox("Priority*", ["Low", "Medium", "High"], key="mech_priority")
            st.text_input("Selected Equipment Type", value=selected_equipment, disabled=True)
            
        with col2:
            location_type = LOCATION_MAP[specific_location]
            st.text_input("Location Type", value=location_type, disabled=True, help="Auto-detected based on Specific Location.")
            equipment_tag = st.text_input("Equipment Name/Tag*", key="mech_equip_tag", placeholder="e.g., P-101A")

           
            work_type = st.selectbox("Select Work Type*", MECH_WORK_TYPES, key="mech_work_type")
            estimated_duration = MECHANICAL_DURATIONS.get(work_type, MECHANICAL_DURATIONS["Default"])
            st.text_input("Estimated Duration (hours)", value=f"{estimated_duration}", disabled=True, help="Auto-calculated based on Work Type.")
        
        
        
        # Dynamic Checklist Renderer
        st.markdown("---")
        checklist_to_render = CHECKLIST_DEFINITIONS['Mechanical'].get(selected_equipment, CHECKLIST_DEFINITIONS['Mechanical']['Default'])
        checklist_results = render_checklist(checklist_to_render, "mech")
      
        
        
        # Overall Findings / Safety 
        st.markdown("---")
        st.subheader("3. Summary & Safety")
        
        overall_findings = st.text_area("Overall Findings / Summary", 
            placeholder="Provide a general summary of the work, or detail any major findings...", height=100, key="mech_findings")
        
        safety_checks_selected = st.multiselect("Safety Checks Performed", 
            options=STANDARD_SAFETY_CHECKS, key="mech_safety")
        
        st.markdown("---")
        submitted = st.form_submit_button("Submit Mechanical Work Order")
        
        if submitted:
            if all([specific_location, equipment_tag, area, selected_equipment, work_type]):
                task_data = {
                    'work_center': 'Mechanical',
                    'location_type': location_type,
                    'specific_location': specific_location,
                    'area': area,
                    'equipment_name': equipment_tag,      # The specific tag
                    'equipment_type': selected_equipment, 
                    'work_type': work_type,              
                    'priority': priority,
                    'estimated_duration': estimated_duration,
                    'checklist_data': checklist_results,
                    'overall_findings': overall_findings,
                    'safety_checks': safety_checks_selected,
                }
                
                success, wo_number = add_task(task_data)
                
                if success:
                    st.success(f"Work Order {wo_number} submitted successfully!", icon="✅")
                    st.balloons()
                else:
                    st.error("Error submitting work order", icon="❌")
            else:
                st.error("Please fill in all required fields (*): Location, Area, Equipment Name/Tag, and Work Type.", icon="❌")



# instrument_form 
def instrument_form():
    st.subheader("📡 Instrument Work Order (PPM)")
    
 
    selected_equipment = st.selectbox(
        "Select Equipment Type*", 
        INST_EQUIPMENT_TYPES, 
        key="inst_equip_type",
        help="Select an equipment type to load the correct checklist below."
    )

    
    with st.form("instrument_form", clear_on_submit=True):
        
        st.subheader("1. Work Order Details")
        
        # --- Metadata ---
        col1, col2 = st.columns(2)
        with col1:
            specific_location = st.selectbox("Specific Location*", ALL_LOCATIONS, key="inst_loc")
            area = st.text_input("Area/Unit*", key="inst_area", placeholder="e.g., Pump 200 Area")
            priority = st.selectbox("Priority*", ["Low", "Medium", "High"], key="inst_priority")
            
            # --- REQUIREMENT 1: Dynamic Equipment Selection (MOVED) ---
            st.text_input("Selected Equipment Type", value=selected_equipment, disabled=True)
            
        with col2:
            location_type = LOCATION_MAP[specific_location]
            st.text_input("Location Type", value=location_type, disabled=True, help="Auto-detected based on Specific Location.")
            equipment_tag = st.text_input("Instrument Name/Tag*", key="inst_equip_tag", placeholder="e.g., CV-101 / PT-101")

            # --- REQUIREMENT 2: Auto-Duration ---
            work_type = st.selectbox("Select Work Type*", INST_WORK_TYPES, key="inst_work_type")
            estimated_duration = INSTRUMENT_DURATIONS.get(work_type, INSTRUMENT_DURATIONS["Default"])
            st.text_input("Estimated Duration (hours)", value=f"{estimated_duration}", disabled=True, help="Auto-calculated based on Work Type.")
            # --- End Requirement 2 ---

        
        # --- REQUIREMENT 1: Call Dynamic Checklist Renderer ---
        st.markdown("---")
        checklist_to_render = CHECKLIST_DEFINITIONS['Instrument'].get(selected_equipment, CHECKLIST_DEFINITIONS['Instrument']['Default'])
        checklist_results = render_checklist(checklist_to_render, "inst")
        # --- End Requirement 1 ---
        
        
        # --- Overall Findings / Safety ---
        st.markdown("---")
        st.subheader("3. Summary & Safety")
        
        overall_findings = st.text_area("Overall Findings / Summary", 
            placeholder="Provide a general summary of the work, or detail any major findings...", height=100, key="inst_findings")
        
        safety_checks_selected = st.multiselect("Safety Checks Performed", 
            options=STANDARD_SAFETY_CHECKS, key="inst_safety")
        
        st.markdown("---")
        submitted = st.form_submit_button("Submit Instrument Work Order")
        
        if submitted:
            if all([specific_location, equipment_tag, area, selected_equipment, work_type]):
                task_data = {
                    'work_center': 'Instrument',
                    'location_type': location_type,
                    'specific_location': specific_location,
                    'area': area,
                    'instrument_name': equipment_tag,     # The specific tag
                    'instrument_type': selected_equipment, # The category (Control Valve, etc)
                    'work_type': work_type,               # The work type (Calibration, etc)
                    'priority': priority,
                    'estimated_duration': estimated_duration,
                    'checklist_data': checklist_results,
                    'overall_findings': overall_findings,
                    'safety_checks': safety_checks_selected,
                }
                
                success, wo_number = add_task(task_data)
                
                if success:
                    st.success(f"Work Order {wo_number} submitted successfully!", icon="✅")
                    st.balloons()
                else:
                    st.error("Error submitting work order", icon="❌")
            else:
                st.error("Please fill in all required fields (*): Location, Area, Equipment Type, Instrument Name/Tag, and Work Type.", icon="❌")
# --- END OF MODIFIED BLOCK 5 ---


# --- MODIFIED LOGIN PAGE ---
def login_page():
    # Center the entire login block using columns
    # [1, 1.5, 1] creates a centered column that is wider than the side spacers
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2: # Main content column
        # --- MODIFICATION: Center title and subtitle ---
        st.markdown(
            "<h1 style='text-align: center;'>Intelligent Workflow Automation With Decision Centric Support (IWA-DCS) For Maintenance Excellence.</h1>", 
            unsafe_allow_html=True
        )
        st.markdown(
            "<h3 style='text-align: center;'>Oil & Gas Maintenance Operations</h3>", 
            unsafe_allow_html=True
        )
        # --- END OF MODIFICATION ---
        st.markdown("---")
        
        with st.form("login_form"):
            # Removed emoji
            st.subheader("System Login")
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            # Removed demo data button and made login button full-width
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username and password:
                    authenticated, user_data = authenticate_user(username, password)
                    if authenticated:
                        st.session_state.authenticated = True
                        st.session_state.user_data = user_data
                        st.session_state.current_page = "dashboard"
                        st.success(f"Welcome back, {user_data['name']}!", icon="👋")
                        st.rerun()
                    else:
                        st.error("Invalid username or password", icon="❌")
                else:
                    st.error("Please enter both username and password", icon="⚠️")
            
            # Removed the "Initialize Demo Data" button and its logic
            # The 'with col2' block containing demo accounts and locations is also removed
# --- END OF MODIFIED LOGIN PAGE ---


# --- Notification Display Function ---
def display_notifications():
    """Fetches and displays dismissible notifications for the current user."""
    try:
        notifications = get_unread_notifications(st.session_state.user_data['username'])
        if notifications:
            st.warning("You have unread notifications:", icon="🔔")
            for notif in notifications:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{notif['timestamp'][:16]}**: {notif['message']}")
                with col2:
                    if st.button("Dismiss", key=f"dismiss_{notif['id']}", use_container_width=True):
                        if mark_notification_read(notif['id']):
                            st.rerun()
                        else:
                            st.error("Failed to dismiss. Please try again.")
            st.markdown("---")
    except Exception as e:
        # This might fail on first login before db is fully ready, so we fail silently
        pass

# --- MODIFIED BLOCK 7: main_dashboard (Request 2: Add Findings Analysis Nav) ---
def main_dashboard():
    st.title(f"🏭 Welcome, {st.session_state.user_data['name']}!")
    st.markdown("### Enterprise Maintenance Management System")
    
    # --- Display notifications at the top of the dashboard ---
    display_notifications()
    
    # Sidebar Navigation
    st.sidebar.title("Main Navigation")
    
    # User info in sidebar
    st.sidebar.markdown(f"""
    👤 **Name:** {st.session_state.user_data['name']}  
    🎯 **Role:** {st.session_state.user_data['role'].title()}  
    🔧 **Work Center:** {st.session_state.user_data['work_center']}  
    📧 **Email:** {st.session_state.user_data.get('email', 'N/A')}
    """)

    # Navigation options based on role
    user_role = st.session_state.user_data['role']
    
    if user_role in ['admin', 'supervisor']:
        nav_options = [
            "📊 Dashboard Overview",
            "📝 Submit New Work Order",
            "📋 My Submitted Work Orders",
            "🏗️ Work Center Queue",
            "✅ Work Order Review Center",
            "📍 Location Analytics",
            "🛡️ Compliance Dashboard",
            "📈 Performance Trends",
            "🎯 KPI Predictions",
            "🔬 Findings Analysis", # Request 2: New Page
            "👥 User Management",
            "👤 My Profile"
        ]
    else: # 'user' role
        nav_options = [
            "📊 Dashboard Overview",
            "📝 Submit New Work Order",
            "📋 My Submitted Work Orders",
            "🏗️ Work Center Queue",
            "👤 My Profile"
        ]
    
    selected_page = st.sidebar.radio("Navigate to", nav_options)
    
    # Logout button
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Logout from System", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.current_page = "login"
        st.rerun()
    
    # Page routing
    if selected_page == "📊 Dashboard Overview":
        dashboard_overview()
    elif selected_page == "📝 Submit New Work Order":
        submit_task_page()
    elif selected_page == "📋 My Submitted Work Orders":
        my_tasks_page()
    elif selected_page == "🏗️ Work Center Queue":
        work_center_tasks_page()
    elif selected_page == "✅ Work Order Review Center":
        if user_role in ['admin', 'supervisor']:
            task_approval_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
    elif selected_page == "📍 Location Analytics":
        if user_role in ['admin', 'supervisor']:
            location_analytics_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
    elif selected_page == "🛡️ Compliance Dashboard":
        if user_role in ['admin', 'supervisor']:
            compliance_checksheet_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
            
    # --- Request 2: Routing for new Findings page ---
    elif selected_page == "🔬 Findings Analysis":
        if user_role in ['admin', 'supervisor']:
            findings_analysis_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
    # --- End of Request 2 ---
            
    elif selected_page == "📈 Performance Trends":
        if user_role in ['admin', 'supervisor']:
            performance_trends_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
    elif selected_page == "🎯 KPI Predictions":
        if user_role in ['admin', 'supervisor']:
            kpi_predictions_page()
        else:
            st.warning("Access denied. Supervisor/Admin role required.", icon="⛔")
    elif selected_page == "👥 User Management":
        if user_role == 'admin':
            user_management_page()
        else:
            st.warning("Admin access required.", icon="⛔")
    elif selected_page == "👤 My Profile":
        profile_page()
# --- END OF MODIFIED BLOCK 7 ---


# --- MODIFIED BLOCK 8: dashboard_overview (Request 1: Show WO#) ---
def dashboard_overview():
    st.header("📊 System Overview Dashboard")
    
    all_tasks = get_all_tasks()
    kpis = calculate_kpis(all_tasks)
    
    # Main KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        target = 80
        delta = kpis['approval_rate'] - target
        st.metric(
            "Overall Approval Rate", 
            f"{kpis['approval_rate']:.1f}%", 
            delta=f"{delta:+.1f}%",
            delta_color="normal" if kpis['approval_rate'] >= target else "inverse",
            help="Target: 80% and above"
        )
    
    with col2:
        st.metric("Total Work Orders", kpis['total_tasks'])
    
    with col3:
        completion_rate = (kpis['completed_tasks'] / kpis['total_tasks'] * 100) if kpis['total_tasks'] > 0 else 0
        st.metric("Work Order Completion Rate", f"{completion_rate:.1f}%")
    
    with col4:
        st.metric("Avg Completion Time", f"{kpis['avg_completion_time']:.1f} hours")
    
    st.markdown("---")
    
    # User-specific stats
    if st.session_state.user_data['role'] in ['user']:
        user_tasks = get_tasks_by_filters({'username': st.session_state.user_data['username']})
        user_pending = len([t for t in user_tasks if t['status'] == 'pending'])
        user_approved = len([t for t in user_tasks if t['status'] == 'approved'])
        user_rejected = len([t for t in user_tasks if t['status'] == 'rejected'])
        
        st.subheader("👤 Your Personal Statistics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("My Total Work Orders", len(user_tasks))
        with col2:
            st.metric("Pending Approval", user_pending)
        with col3:
            st.metric("Approved Work Orders", user_approved)
        with col4:
            st.metric("Rejected Work Orders", user_rejected)
        st.markdown("---")

    # Recent Activity
    st.subheader("🕒 Recent System Activity")
    recent_tasks = sorted(all_tasks, key=lambda x: x.get('submission_date', ''), reverse=True)[:8]
    
    if recent_tasks:
        for task in recent_tasks:
            status = task.get('status', 'unknown')
            status_icon = "🟢" if status == 'approved' else "🟡" if status == 'pending' else "🔴"
            location_icon = "🏢" if task.get('location_type') == 'Onshore' else "🛳️"
            
            st.markdown(f"""
            <div style="padding: 10px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>{status_icon} {task.get('work_order_number', 'N/A')}:</strong> {task.get('equipment_name', task.get('instrument_name', 'Task'))}
                    <br>
                    <small>{location_icon} {task.get('specific_location', 'N/A')} | 👤 {task.get('submitted_by_name', 'N/A')}</small>
                </div>
                <div>
                    <em>{status.title()}</em>
                    <br>
                    <small>{task.get('submission_date', 'N/A')[:10]}</small>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
    else:
        st.info("No recent activity found in the system.")
# --- END OF MODIFIED BLOCK 8 ---


# Submit Task Page
def submit_task_page():
    st.header("📝 Submit New Maintenance Work Order")
    
    user_work_center = st.session_state.user_data['work_center']
    
    if user_work_center == 'Electrical':
        electrical_form()
    elif user_work_center == 'Mechanical':
        mechanical_form()
    elif user_work_center == 'Instrument':
        instrument_form()
    elif user_work_center == 'All':
        # Admin/Supervisor can choose any form
        st.subheader("Select Work Center Form")
        form_type = st.selectbox("Choose Work Center", 
                                     ["Electrical", "Mechanical", "Instrument"])
        if form_type == "Electrical":
            electrical_form()
        elif form_type == "Mechanical":
            mechanical_form()
        else:
            instrument_form()
    else:
        st.warning("No work center assigned. Please contact administrator.")

# --- MODIFIED BLOCK 9: my_tasks_page (Updated for New Fields) ---
def my_tasks_page():
    st.header("📋 My Submitted Work Orders")
    
    user_tasks = get_tasks_by_filters({'username': st.session_state.user_data['username']})
    
    if not user_tasks:
        st.info("You haven't submitted any work orders yet. Use the 'Submit New Work Order' page to get started.")
        return
    
    # Status filter for user
    status_filter = st.multiselect(
        "Filter by Status",
        options=['pending', 'approved', 'rejected'],
        default=['pending', 'approved', 'rejected']
    )
    
    filtered_tasks = [t for t in user_tasks if t['status'] in status_filter]
    
    for task in filtered_tasks:
        with st.container(border=True):
            status_color = {'pending': 'orange', 'approved': 'green', 'rejected': 'red'}
            status_icon = {'pending': '🟡', 'approved': '🟢', 'rejected': '🔴'}
            location_icon = "🏢" if task.get('location_type') == 'Onshore' else "🛳️"
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"""
                <div style="padding: 10px; border-left: 5px solid {status_color[task['status']]}; border-radius: 5px;">
                    <h4 style="margin: 0;">{task.get('work_order_number', 'N/A')}: {task.get('equipment_name', task.get('instrument_name', 'Task'))}</h4>
                    <p style="margin: 5px 0; color: #666;">
                        {location_icon} <strong>Location:</strong> {task.get('specific_location', 'N/A')} ({task.get('location_type', 'N/A')}) | 
                        🔧 <strong>Work Center:</strong> {task['work_center']} |
                        📅 <strong>Submitted:</strong> {task['submission_date'][:10]}
                    </p>
                    <p style="margin: 5px 0;"><strong>Area/Unit:</strong> {task.get('area', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Equipment Type:</strong> {task.get('equipment_type', task.get('instrument_type', 'N/A'))}</p>
                    <p style="margin: 5px 0;"><strong>Work Type:</strong> {task.get('work_type', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Priority:</strong> {task.get('priority', 'Medium')}</p>
                    <p style="margin: 5px 0;"><strong>Summary:</strong> {task.get('overall_findings', 'N/A')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if task.get('feedback'):
                    st.info(f"**Supervisor Feedback:** {task['feedback']}")
            
            with col2:
                st.write(f"**Status:** {task['status'].title()} {status_icon[task['status']]}")
                if task['status'] == 'approved':
                    st.success("Approved ✅")
                    if task.get('reviewed_by'):
                        st.write(f"By: {task['reviewed_by']}")
                elif task['status'] == 'rejected':
                    st.error("Rejected ❌")
                    if task.get('reviewed_by'):
                        st.write(f"By: {task['reviewed_by']}")
                else:
                    st.warning("Pending Review ⏳")
# --- END OF MODIFIED BLOCK 9 ---


# --- MODIFIED BLOCK 10: work_center_tasks_page (Updated for New Fields) ---
def work_center_tasks_page():
    st.header("🏗️ Work Center Queue")
    
    user_wc = st.session_state.user_data['work_center']
    
    if user_wc == 'All':
        # Admin/Supervisor can filter by work center
        work_center_filter = st.selectbox(
            "Select Work Center to View", 
            ["All", "Electrical", "Mechanical", "Instrument"]
        )
    else:
        # Normal user is locked to their work center
        work_center_filter = user_wc
        st.subheader(f"Displaying tasks for: {user_wc}")

    
    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.multiselect(
            "Filter by Status",
            options=['pending', 'approved', 'rejected'],
            default=['pending', 'approved', 'rejected']
        )
    with col2:
        location_filter = st.multiselect(
            "Filter by Location Type",
            options=['Onshore', 'Offshore'],
            default=['Onshore', 'Offshore']
        )
    with col3:
        priority_filter = st.multiselect(
            "Filter by Priority",
            options=['Low', 'Medium', 'High'],
            default=['Low', 'Medium', 'High']
        )
    
    # Build filter dictionary
    task_filters = {
        'status': status_filter,
        'location_type': location_filter
    }
    
    if work_center_filter != 'All':
        task_filters['work_center'] = work_center_filter
        
    tasks = get_tasks_by_filters(task_filters)
    
    # Apply priority filter (post-query)
    tasks = [t for t in tasks if t.get('priority', 'Medium') in priority_filter]
    
    if not tasks:
        st.info(f"No tasks found for selected filters.")
        return
    
    st.metric(f"Total Tasks Matching Filters", len(tasks))
    
    for task in tasks:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                location_icon = "🏢" if task.get('location_type') == 'Onshore' else "🛳️"
                status_icon = "🟢" if task['status'] == 'approved' else "🟡" if task['status'] == 'pending' else "🔴"
                
                st.write(f"**{task.get('work_order_number', 'N/A')}: {task.get('equipment_name', task.get('instrument_name', 'Task'))}** {status_icon}")
                st.write(f"{location_icon} **Location:** {task.get('specific_location', 'N/A')} | **Area:** {task.get('area', 'N/A')}")
                st.write(f"**By:** {task['submitted_by_name']} | **Date:** {task['submission_date'][:10]}")
                st.write(f"**Eq. Type:** {task.get('equipment_type', task.get('instrument_type', 'N/A'))} | **Work Type:** {task.get('work_type', 'N/A')}")
                st.write(f"**Summary:** {task.get('overall_findings', 'N/A')}")
                st.write(f"**Priority:** {task.get('priority', 'Medium')} | **Duration:** {task.get('estimated_duration', 'N/A')} hours")
            
            with col2:
                st.write(f"**Status:** {task['status'].title()}")
                if task['status'] == 'approved':
                    st.success("Approved ✅")
                elif task['status'] == 'rejected':
                    st.error("Rejected ❌")
                else:
                    st.warning("Pending ⏳")
                
                if task.get('reviewed_by'):
                    st.write(f"Reviewed by: {task['reviewed_by']}")
# --- END OF MODIFIED BLOCK 10 ---


# --- MODIFIED BLOCK 11: task_approval_page (PDF Buttons Added) ---
def task_approval_page():
    st.header("✅ Work Order Review Center")
    
    pending_tasks = get_tasks_by_filters({'status': ['pending']})
    
    if not pending_tasks:
        st.success("No pending work orders! All caught up.", icon="🎉")
        return
    
    st.metric("Work Orders Pending Approval", len(pending_tasks))
    
    # Filters for approval center
    col1, col2, col3 = st.columns(3)
    with col1:
        work_center_filter = st.multiselect(
            "Work Center",
            options=sorted(list(set(task['work_center'] for task in pending_tasks))),
            default=sorted(list(set(task['work_center'] for task in pending_tasks)))
        )
    with col2:
        location_filter = st.multiselect(
            "Location Type",
            options=sorted(list(set(task.get('location_type', 'Unknown') for task in pending_tasks))),
            default=sorted(list(set(task.get('location_type', 'Unknown') for task in pending_tasks)))
        )
    with col3:
        priority_filter = st.multiselect(
            "Priority",
            options=sorted(list(set(task.get('priority', 'Medium') for task in pending_tasks))),
            default=sorted(list(set(task.get('priority', 'Medium') for task in pending_tasks)))
        )
    
    # Filter tasks
    filtered_tasks = [
        task for task in pending_tasks
        if task['work_center'] in work_center_filter
        and task.get('location_type', 'Unknown') in location_filter
        and task.get('priority', 'Medium') in priority_filter
    ]
    
    for task in filtered_tasks:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                location_icon = "🏢" if task.get('location_type') == 'Onshore' else "🛳️"
                
                st.markdown(f"""
                <div style="padding: 15px; border-left: 5px solid orange; background-color: #F5F5F5; border-radius: 8px;">
                    <h4 style="margin: 0;">{task.get('work_order_number', 'N/A')}: {task.get('equipment_name', task.get('instrument_name', 'Task'))}</h4>
                    <p style="margin: 5px 0; color: #666;">
                        {location_icon} <strong>Location:</strong> {task.get('specific_location', 'N/A')} ({task.get('location_type', 'N/A')}) | 
                        🔧 <strong>Work Center:</strong> {task['work_center']} | 
                        ⚡ <strong>Priority:</strong> {task.get('priority', 'Medium')}
                    </p>
                    <p style="margin: 5px 0;"><strong>Submitted by:</strong> {task['submitted_by_name']}</p>
                    <p style="margin: 5px 0;"><strong>Area/Unit:</strong> {task.get('area', 'N/A')}</p>
                    <p style="margin: 5px 0;"><strong>Estimated Duration:</strong> {task.get('estimated_duration', 'N/A')} hours</p>
                </div>
                """, unsafe_allow_html=True)

                # --- Show NEW CHECKLIST details ---
                with st.expander("Show Checklist, Findings, & Safety Details"):
                    
                    # --- ADDED: Equipment/Work Type ---
                    st.markdown(f"**Equipment Type:** {task.get('equipment_type', task.get('instrument_type', 'N/A'))}")
                    st.markdown(f"**Work Type:** {task.get('work_type', 'N/A')}")
                    st.markdown("---")
                    
                    st.markdown(f"""
                    **Overall Findings / Summary:**
                    > {task.get('overall_findings', 'N/A')}
                    """)
                    st.markdown("---")
                    
                    # --- Request 3: Display Safety Checks ---
                    st.markdown("**Safety Checks Recorded:**")
                    safety_checks = task.get('safety_checks', [])
                    if safety_checks:
                        for check in safety_checks:
                            st.markdown(f"- {check}")
                    else:
                        st.markdown("_No safety checks recorded._")
                    st.markdown("---")
                    # --- End of Request 3 ---
                    
                    # --- NEW: Display Checklist Results ---
                    st.markdown("**Checklist Results:**")
                    checklist_data = task.get('checklist_data', [])
                    if not checklist_data:
                        st.markdown("_No checklist data found._")
                    else:
                        for item in checklist_data:
                            status = item.get('status', 'N/A')
                            status_icon = "🟢" if status == 'PASS' else "🔴" if status == 'FAIL' else "⚪"
                            
                            st.markdown(f"- {status_icon} **{item.get('task', 'N/A')}** (Status: *{status}*)")
                            if item.get('remarks'):
                                st.info(f"  **Remarks:** {item.get('remarks')}")
                    # --- END OF NEW Checklist Display ---

            
            with col2:
                # --- NEW PDF FEATURES (FOR ADMIN & SUPERVISOR) ---
                if st.session_state.user_data['role'] in ['supervisor', 'admin']:
                    st.write("**Report Generation:**")
                    
                    # 1. Generate PDF in memory
                    try:
                        pdf_bytes = generate_task_pdf(task)
                        wo_number = task.get('work_order_number', 'task')
                        file_name = f"{wo_number}_{task['work_center']}.pdf"

                        # 2. Download Button
                        st.download_button(
                            label="⬇️ Download PDF",
                            data=pdf_bytes,
                            file_name=file_name,
                            mime="application/pdf",
                            key=f"download_pdf_{task['id']}",
                            use_container_width=True
                        )
                        
                        # --- REMOVED PREVIEW PDF LINK AND SEPARATOR ---
                    
                    except Exception as e:
                        st.error(f"Failed to generate PDF: {e}", icon="❌")

                # --- SUPERVISOR-ONLY ACTIONS ---
                if st.session_state.user_data['role'] == 'supervisor':
                    st.write("**Review Actions:**")
                    
                    if st.button("✅ Approve", key=f"approve_{task['id']}", use_container_width=True):
                        if update_task_status(task['id'], 'approved', "Task approved as per standards", st.session_state.user_data['name']):
                            st.success("Work order approved successfully!", icon="✅")
                            st.rerun()
                    
                    with st.popover("❌ Reject Task"):
                        st.write("Provide reason for rejection:")
                        feedback = st.text_area(
                            "Rejection Reason:",
                            key=f"feedback_{task['id']}",
                            placeholder="Please provide detailed reason for rejection...",
                            height=100
                        )
                        if st.button("Confirm Rejection", key=f"reject_{task['id']}"):
                            if feedback.strip():
                                if update_task_status(task['id'], 'rejected', feedback, st.session_state.user_data['name']):
                                    st.success("Work order rejected with feedback!", icon="✅")
                                    st.rerun()
                            else:
                                st.error("Please provide a reason for rejection.", icon="❌")
                                
                elif st.session_state.user_data['role'] == 'admin':
                    st.info("Admins can generate reports. Only Supervisors can approve or reject tasks.")
# --- END OF MODIFIED BLOCK 11 ---


def location_analytics_page():
    st.header("📍 Location-Based Analytics")
    
    all_tasks = get_all_tasks()
    
    # Location type selection
    location_type = st.selectbox("Select Location Type", ["All", "Onshore", "Offshore"])
    
    if location_type != "All":
        tasks = [t for t in all_tasks if t.get('location_type') == location_type]
    else:
        tasks = all_tasks
    
    if not tasks:
        st.info("No task data found for the selected location.")
        return
        
    kpis = calculate_kpis(tasks)
    
    # Location KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Work Orders", len(tasks))
    with col2:
        st.metric("Approval Rate", f"{kpis['approval_rate']:.1f}%")
    with col3:
        completion_rate = (kpis['completed_tasks'] / len(tasks) * 100) if tasks else 0
        st.metric("Completion Rate", f"{completion_rate:.1f}%")
    with col4:
        st.metric("Avg Completion Time", f"{kpis['avg_completion_time']:.1f}h")
    
    st.markdown("---")
    
    # Location performance charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Location type performance
        if kpis['location_type_performance'] and location_type == "All":
            loc_type_data = pd.DataFrame({
                'Location Type': list(kpis['location_type_performance'].keys()),
                'Approval Rate': list(kpis['location_type_performance'].values())
            })
            fig = px.bar(loc_type_data, x='Location Type', y='Approval Rate',
                         title="Approval Rate by Location Type",
                         color='Approval Rate', color_continuous_scale=['red', 'yellow', 'green'])
            fig.add_hline(y=80, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Show work center breakdown for the selected location type
            wc_data = pd.DataFrame({
                'Work Center': list(kpis['work_center_performance'].keys()),
                'Approval Rate': list(kpis['work_center_performance'].values())
            })
            fig_wc = px.bar(wc_data, x='Work Center', y='Approval Rate',
                            title=f"Approval Rate by Work Center ({location_type})",
                            color='Approval Rate', color_continuous_scale=['red', 'yellow', 'green'])
            fig_wc.add_hline(y=80, line_dash="dash", line_color="red")
            st.plotly_chart(fig_wc, use_container_width=True)

    
    with col2:
        # Specific location performance
        if kpis['location_performance']:
            loc_data = pd.DataFrame({
                'Location': list(kpis['location_performance'].keys()),
                'Approval Rate': list(kpis['location_performance'].values())
            })
            
            if location_type != "All":
                valid_locations = [loc for loc, type in LOCATION_MAP.items() if type == location_type]
                loc_data = loc_data[loc_data['Location'].isin(valid_locations)]

            fig = px.bar(loc_data, x='Location', y='Approval Rate',
                         title="Approval Rate by Specific Location",
                         color='Approval Rate', color_continuous_scale=['red', 'yellow', 'green'])
            fig.add_hline(y=80, line_dash="dash", line_color="red")
            st.plotly_chart(fig, use_container_width=True)


# --- Compliance Checksheet Page ---
def compliance_checksheet_page():
    st.header("🛡️ Location Compliance Dashboard")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("New Compliance Report")
        with st.form("compliance_form", clear_on_submit=True):
            selected_location = st.selectbox("Select Location*", ALL_LOCATIONS)
            report_date = st.date_input("Report Date*", datetime.now())
            inspector_name = st.text_input("Inspector Name*", value=st.session_state.user_data['name'])
            
            st.markdown("---")
            st.markdown("**Safety Compliance Checks**")
            check_1 = st.checkbox("Safety Permits Verified and Active (e.g., PTW)")
            check_2 = st.checkbox("Job Safety Analysis (JSA) Complete and Reviewed")
            check_3 = st.checkbox("Area Secured & Barricaded Correctly")
            check_4 = st.checkbox("LOTO (Lockout/Tagout) Applied where Required")
            
            st.markdown("**Equipment Compliance Checks**")
            check_5 = st.checkbox("Tools & Equipment Inspected and Certified")
            check_6 = st.checkbox("Fire-Fighting Equipment Accessible and Inspected")
            check_7 = st.checkbox("PPE Compliance Met by All Personnel")
            
            comments = st.text_area("Compliance Notes / Non-conformances",
                                    placeholder="Detail any findings, non-conformances, or areas for improvement...")
            
            submitted = st.form_submit_button("Submit Compliance Report")
            
            if submitted:
                if not all([selected_location, report_date, inspector_name]):
                    st.error("Please fill in all required fields (*)", icon="❌")
                else:
                    report_data = {
                        'location': selected_location,
                        'report_date': report_date.isoformat(),
                        'inspector': inspector_name,
                        'inspector_username': st.session_state.user_data['username'],
                        'permits_verified': check_1,
                        'jsa_complete': check_2,
                        'area_secured': check_3,
                        'loto_applied': check_4,
                        'tools_certified': check_5,
                        'fire_equipment_ok': check_6,
                        'ppe_ok': check_7,
                        'comments': comments,
                        'submission_timestamp': datetime.now().isoformat()
                    }
                    if save_compliance_report(report_data):
                        st.success(f"Compliance report for {selected_location} submitted successfully!", icon="✅")
                    else:
                        st.error("Failed to submit report. Check database connection.", icon="❌")

    with col2:
        st.subheader("Past Compliance Reports")
        filter_location = st.selectbox("View Reports For Location", ALL_LOCATIONS, key="view_location")
        
        reports = get_compliance_reports(filter_location)
        
        if not reports:
            st.info(f"No compliance reports found for {filter_location}.")
        else:
            st.metric("Total Reports Found", len(reports))
            for report in reports:
                with st.expander(f"Report: {report['report_date']} (Inspector: {report['inspector']})"):
                    st.markdown(f"**Location:** {report['location']}")
                    st.markdown(f"**Inspector:** {report['inspector']}")
                    st.markdown(f"**Report Date:** {report['report_date']}")
                    st.markdown("---")
                    
                    checks = {
                        "Permits Verified": report.get('permits_verified', False),
                        "JSA Complete": report.get('jsa_complete', False),
                        "Area Secured": report.get('area_secured', False),
                        "LOTO Applied": report.get('loto_applied', False),
                        "Tools Certified": report.get('tools_certified', False),
                        "Fire Equipment OK": report.get('fire_equipment_ok', False),
                        "PPE OK": report.get('ppe_ok', False),
                    }
                    
                    all_compliant = all(checks.values())
                    
                    if all_compliant:
                        st.success("✅ All checks passed.")
                    else:
                        st.error("❌ Non-compliance found.")
                        
                    for check, status in checks.items():
                        st.markdown(f"- {check}: {'✅' if status else '❌'}")
                        
                    st.markdown("**Inspector Comments/Non-conformances:**")
                    st.info(f"{report.get('comments', 'N/A')}")


# --- NEW BLOCK 7: Findings Analysis Page (Request 2) ---
# --- UPDATED to use 'overall_findings' ---
def findings_analysis_page():
    st.header("🔬 Findings & Observations Analysis")
    
    all_tasks = get_all_tasks()
    
    # Filter for tasks that have findings
    tasks_with_findings = [
        t for t in all_tasks 
        if t.get('overall_findings') 
        and t.get('overall_findings').strip() != 'N/A'
    ]
    
    if not tasks_with_findings:
        st.info("No tasks with 'Overall Findings / Summary' have been submitted yet.")
        return

    st.sidebar.markdown("---")
    st.sidebar.subheader("Findings Filters")
    
    # Filters
    wc_filter = st.sidebar.multiselect(
        "Filter by Work Center",
        options=sorted(list(set(t['work_center'] for t in tasks_with_findings))),
        default=sorted(list(set(t['work_center'] for t in tasks_with_findings)))
    )
    
    loc_filter = st.sidebar.multiselect(
        "Filter by Location Type",
        options=sorted(list(set(t.get('location_type', 'N/A') for t in tasks_with_findings))),
        default=sorted(list(set(t.get('location_type', 'N/A') for t in tasks_with_findings)))
    )
    
    search_term = st.sidebar.text_input("Search Findings Text").lower()
    
    # Apply filters
    filtered_tasks = [
        t for t in tasks_with_findings
        if t['work_center'] in wc_filter
        and t.get('location_type', 'N/A') in loc_filter
        and (search_term in t.get('overall_findings', '').lower() if search_term else True)
    ]
    
    st.metric("Total Findings Records Found", len(filtered_tasks))
    st.markdown("---")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Common Keywords in Findings")
        
        # Get list of all text
        findings_text_list = [t.get('overall_findings', '') for t in filtered_tasks]
        
        if findings_text_list:
            common_words = analyze_findings_text(findings_text_list)
            
            if common_words:
                df_words = pd.DataFrame(common_words, columns=['Word', 'Count'])
                fig = px.bar(df_words, x='Count', y='Word', orientation='h',
                             title="Top 20 Common Keywords",
                             color='Count', color_continuous_scale='cividis_r')
                fig.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No common keywords found after filtering.")
        else:
            st.info("No findings text in filtered results.")

    with col2:
        st.subheader("Raw Findings Log")
        
        if not filtered_tasks:
            st.info("No tasks match the current filters.")
        
        for task in filtered_tasks:
            location_icon = "🏢" if task.get('location_type') == 'Onshore' else "🛳️"
            exp_header = f"{task.get('work_order_number', 'N/A')}: {task.get('equipment_name', task.get('instrument_name', 'Task'))}"
            
            with st.expander(exp_header):
                st.markdown(f"""
                - **Date:** {task.get('submission_date', 'N/A')[:10]}
                - **Location:** {location_icon} {task.get('specific_location', 'N/A')}
                - **Work Center:** {task.get('work_center', 'N/A')}
                - **Submitted By:** {task.get('submitted_by_name', 'N/A')}
                """
                )
                st.info(f"**Overall Findings:**\n\n{task.get('overall_findings')}")
# --- END OF NEW BLOCK 7 ---


def performance_trends_page():
    st.header("📈 Performance Trend Analysis")
    
    all_tasks = get_all_tasks()
    prediction = predict_kpi_trend(all_tasks)
    
    if prediction['historical_data']:
        df = pd.DataFrame(prediction['historical_data'])
        
        # Create trend chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df['date'], y=df['approval_rate'], mode='lines+markers', 
                                 name='Approval Rate', line=dict(color='blue', width=3)))
        fig.add_trace(go.Scatter(x=df['date'], y=df['completion_rate'], mode='lines+markers',
                                 name='Completion Rate', line=dict(color='green', width=3)))
        fig.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Target: 80%")
        fig.update_layout(
            title="Performance Trends Over Time",
            xaxis_title="Date",
            yaxis_title="Rate (%)",
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough historical data for trend analysis. Continue using the system to generate data.")

def kpi_predictions_page():
    st.header("🎯 KPI Predictions & Achievement Analysis")
    
    all_tasks = get_all_tasks()
    prediction = predict_kpi_trend(all_tasks)
    
    TARGET_KPI = 80
    
    # Prediction metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Approval Rate", f"{prediction['current_rate']:.1f}%")
    
    with col2:
        delta = prediction['predicted_rate'] - prediction['current_rate']
        st.metric(
            "7-Day Prediction", 
            f"{prediction['predicted_rate']:.1f}%", 
            delta=f"{delta:+.1f}%"
        )
    
    with col3:
        achievement_color = "normal" if prediction['achievement_probability'] >= 70 else "off"
        st.metric(
            f"Probability of Achieving {TARGET_KPI}%", 
            f"{prediction['achievement_probability']:.1f}%",
            delta_color=achievement_color
        )
    
    st.markdown("---")
    
    # Achievement probability gauge
    st.subheader("🎯 KPI Achievement Probability Gauge")
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=prediction['achievement_probability'],
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Probability of Achieving {TARGET_KPI}% Target"},
        delta={'reference': 50},
        gauge={
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 30], 'color': "red"},
                {'range': [30, 70], 'color': "yellow"},
                {'range': [70, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 70
            }
        }
    ))
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    # Recommendations based on probability
    st.subheader("💡 Recommendations")
    
    if prediction['achievement_probability'] < 50:
        st.error("""
        **🚨 Immediate Action Required**
        - Review and accelerate pending work order approvals
        - Identify bottlenecks in low-performing work centers
        - Conduct training sessions for technicians
        - Implement daily performance monitoring
        - Focus on locations with lowest approval rates
        """)
    elif prediction['achievement_probability'] < 70:
        st.warning("""
        **⚠️ Improvement Needed**
        - Monitor trends closely
        - Provide additional support to struggling teams
        - Streamline approval processes
        - Set weekly performance targets
        """)
    else:
        st.success("""
        **✅ Good Performance**
        - Maintain current processes
        - Share best practices across teams
        - Continue regular monitoring
        - Focus on continuous improvement
        """)

def user_management_page():
    st.header("👥 User Management System")
    
    if st.session_state.user_data['role'] != 'admin':
        st.error("Administrator access required for user management.", icon="⛔")
        return
    
    # Display current users
    st.subheader("Current System Users")
    
    user_list = []
    # Fetch users from Firebase
    try:
        users_ref = db.collection(USERS_COLLECTION)
        users = users_ref.stream()
        
        for user in users:
            user_data = user.to_dict()
            user_list.append({
                'Username': user.id,
                'Name': user_data.get('name'),
                'Role': user_data.get('role'),
                'Work Center': user_data.get('work_center'),
                'Email': user_data.get('email')
            })
        
        if user_list:
            users_df = pd.DataFrame(user_list)
            st.dataframe(users_df, use_container_width=True)
        else:
            st.info("No users found in the database. Use 'Initialize Demo Data' on the login page.")
            
    except Exception as e:
        st.error(f"Error fetching users: {e}", icon="❌")

    
    # Add new user form
    st.subheader("Add New User")
    with st.form("add_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            new_username = st.text_input("Username*")
            new_name = st.text_input("Full Name*")
            new_email = st.text_input("Email Address*")
            
        with col2:
            new_role = st.selectbox("Role*", ["user", "supervisor", "admin"])
            new_work_center = st.selectbox("Work Center*", ["Electrical", "Mechanical", "Instrument", "All"])
            new_password = st.text_input("Temporary Password*", type="password")
        
        if st.form_submit_button("Create User Account"):
            if all([new_username, new_name, new_email, new_password]):
                try:
                    user_data = {
                        'username': new_username,
                        'name': new_name,
                        'email': new_email,
                        'role': new_role,
                        'work_center': new_work_center,
                        'password': new_password  # WARNING: Plaintext. Use Hashing.
                    }
                    db.collection(USERS_COLLECTION).document(new_username).set(user_data)
                    st.success(f"User account for {new_name} created successfully!", icon="✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating user: {e}", icon="❌")
            else:
                st.error("Please fill in all required fields (*)", icon="❌")
    
    # --- Remove User Form ---
    st.subheader("Remove User")
    if user_list:
        current_admin_username = st.session_state.user_data.get('username')
        # Ensure admin cannot delete themselves
        deletable_users = [user['Username'] for user in user_list if user['Username'] != current_admin_username]
        
        if not deletable_users:
            st.info("No other users to remove.")
        else:
            with st.form("delete_user_form"):
                user_to_delete = st.selectbox("Select User to Remove*", options=deletable_users)
                st.warning("⚠️ This action is permanent and cannot be undone.")
                
                delete_submitted = st.form_submit_button("❌ Remove User Account")
                
                if delete_submitted:
                    if user_to_delete:
                        if delete_user_from_db(user_to_delete):
                            st.success(f"User '{user_to_delete}' has been removed successfully.", icon="✅")
                            st.rerun()
                        else:
                            st.error(f"Failed to remove user '{user_to_delete}'.", icon="❌")
                    else:
                        st.error("Please select a user to remove.", icon="❌")

def profile_page():
    st.header("👤 My Profile & Statistics")
    
    user_data = st.session_state.user_data
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Personal Information")
        st.write(f"**👤 Name:** {user_data['name']}")
        st.write(f"**🔑 Username:** {user_data.get('username', 'N/A')}")
        st.write(f"**🎯 Role:** {user_data['role'].title()}")
        st.write(f"**🔧 Work Center:** {user_data['work_center']}")
        st.write(f"**📧 Email:** {user_data.get('email', 'N/A')}")
        
        # --- Profile actions ---
        st.subheader("Account Actions")
        
        with st.expander("🔄 Update Profile Information"):
            with st.form("update_profile_form"):
                st.write("Update your personal details:")
                new_name = st.text_input("Full Name", value=user_data['name'])
                new_email = st.text_input("Email Address", value=user_data.get('email', ''))
                
                if st.form_submit_button("Save Changes"):
                    if update_user_profile_details(user_data.get('username'), new_name, new_email):
                        # Update session state immediately
                        st.session_state.user_data['name'] = new_name
                        st.session_state.user_data['email'] = new_email
                        st.success("Profile updated successfully!", icon="✅")
                        st.rerun()
                    else:
                        st.error("Failed to update profile.", icon="❌")
        
        with st.expander("🔒 Change Password"):
            with st.form("change_password_form"):
                st.write("Update your password:")
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")
                
                if st.form_submit_button("Update Password"):
                    if not all([current_password, new_password, confirm_password]):
                        st.error("Please fill in all password fields.", icon="❌")
                    elif new_password != confirm_password:
                        st.error("New passwords do not match.", icon="❌")
                    else:
                        success, message = update_user_password(
                            user_data.get('username'), 
                            current_password, 
                            new_password
                        )
                        if success:
                            st.success(message, icon="✅")
                        else:
                            st.error(message, icon="❌")

    with col2:
        st.subheader("Performance Statistics")
        user_tasks = get_tasks_by_filters({'username': user_data.get('username', '')})
        total_tasks = len(user_tasks)
        pending_tasks = len([t for t in user_tasks if t['status'] == 'pending'])
        approved_tasks = len([t for t in user_tasks if t['status'] == 'approved'])
        rejected_tasks = len([t for t in user_tasks if t['status'] == 'rejected'])
        
        st.metric("Total Work Orders Submitted", total_tasks)
        st.metric("Pending Approval", pending_tasks)
        st.metric("Approved Work Orders", approved_tasks)
        st.metric("Rejected Work Orders", rejected_tasks)
        
        if total_tasks > 0:
            # Personal approval rate based on completed tasks
            completed_tasks = approved_tasks + rejected_tasks
            approval_rate = (approved_tasks / completed_tasks * 100) if completed_tasks > 0 else 0
            st.metric("Personal Approval Rate", f"{approval_rate:.1f}%")
            
            # Location distribution
            onshore_tasks = len([t for t in user_tasks if t.get('location_type') == 'Onshore'])
            offshore_tasks = len([t for t in user_tasks if t.get('location_type') == 'Offshore'])
            
            if onshore_tasks > 0 or offshore_tasks > 0:
                st.write("**Work Order Location Breakdown:**")
                loc_df = pd.DataFrame({
                    'Location Type': ['Onshore', 'Offshore'],
                    'Tasks': [onshore_tasks, offshore_tasks]
                })
                fig = px.pie(loc_df, names='Location Type', values='Tasks', title='Your Submissions by Location')
                st.plotly_chart(fig, use_container_width=True)

# Main Application
def main():
    initialize_session_state()
    
    if not st.session_state.authenticated:
        login_page()
    else:
        main_dashboard()

if __name__ == "__main__":
    main()
