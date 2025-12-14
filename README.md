
# Intelligent Workflow Automation with Decision-Centric Support (IWA-DCS)
## Project Overview
This project is a web-based Rapid Application Development (RAD) prototype designed to digitize maintenance workflows. It replaces manual paper checksheets with dynamic digital forms, automated approval routing, and predictive analytics.

**Tech Stack:**
* **Frontend:** Streamlit (Python)
* **Backend:** Google Firebase Firestore (NoSQL)
* **Analytics:** Pandas, Plotly, NumPy

---

#Setup Guide

Follow these steps to run the application locally on your machine.

### 1. Prerequisites
Ensure you have the following installed:
* [Python 3.8 or higher](https://www.python.org/downloads/)
* [VS Code](https://code.visualstudio.com/) (Recommended IDE)

### 2. Installation

1.  **Clone the Repository** (or download the ZIP file):
    ```bash
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Create a Virtual Environment** (Recommended):
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(If `requirements.txt` is missing, run: `pip install streamlit firebase-admin pandas plotly numpy`)*

### 3. Firebase Configuration (CRITICAL STEP)

Because this app uses a secure database, you need a private key to access it. **For security reasons, the private key is NOT included in this repository.**

1.  Go to your [Firebase Console](https://console.firebase.google.com/).
2.  Navigate to **Project Settings** > **Service Accounts**.
3.  Click **Generate New Private Key**.
4.  Download the JSON file.
5.  **Rename** the file to `serviceAccountKey.json` (or whatever name matches your code in `main.py`).
6.  **Move** this file into the root folder of this project.

>  WARNING:** Never upload your `serviceAccountKey.json` to GitHub. It contains sensitive passwords. Ensure it is listed in your `.gitignore` file.



# How to Run

1.  Open your terminal/command prompt in the project folder.
2.  Run the Streamlit app:
    ```bash
    streamlit run main.py
    ```
    *(Note: If your main file is named differently, e.g., `app.py`, replace `main.py` with that name).*

3.   The app will automatically open in your default web browser at `http://localhost:8501`.



## 🔑 Login Credentials (For Testing)

Use the following accounts to test the Role-Based Access Control (RBAC):

| Role | Username | Description |
| :--- | :--- | :--- |
| **Technician** | `tech_demo` | Can submit tasks and view checklists. |
| **Supervisor** | `sup_demo` | Can review, approve, and reject tasks. |
| **Admin** | `admin_demo` | Can access KPI analytics and compliance reports. |

*(Note: Passwords are managed via the Firebase Authentication logic or hardcoded for demo purposes—check source code for details).*

---

#Project Structure

* `main.py`: The entry point of the application.
* `modules/`: Contains separate logic files (e.g., UI rendering, database functions).
* `assets/`: Images and static files.
* `requirements.txt`: List of Python libraries required.
* `serviceAccountKey.json`: (Ignored by Git) Your local database key.

