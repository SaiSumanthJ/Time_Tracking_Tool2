
# --- app.py ---
import os
import json
import uuid
import time
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sendgrid
from sendgrid.helpers.mail import Mail

# --- Configuration ---
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDER_EMAIL = os.environ.get('SENDER_EMAIL', 'noreply@yourcompany.com')
TRACKER_APP_FILENAME = 'tracker_app.zip'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', os.path.join(BASE_DIR, 'backend'))
STORAGE_FILE = os.path.join(DATA_DIR, 'storage.json')
SCREENSHOTS_DIR = os.path.join(DATA_DIR, 'screenshots')

# Ensure directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Initialize Flask
app = Flask(__name__, static_folder='static')
CORS(app)

# --- Helpers ---
def load_data():
    if not os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, 'w') as f:
            json.dump({"employees": [], "projects": [], "tasks": [], "timeLogs": [], "screenshots": []}, f)
    with open(STORAGE_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(STORAGE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_id():
    return str(uuid.uuid4())

def send_activation_email(employee):
    activation_link = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/activate/{employee['id']}"
    email_content = f"""
    Hi {employee['name']},
    
    Please activate your account by clicking the link below:
    {activation_link}
    
    Once activated, download the tracker here:
    https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/static/{TRACKER_APP_FILENAME}
    """
    sg = sendgrid.SendGridAPIClient(SENDGRID_API_KEY)
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=employee['email'],
        subject='Activate Your Time Tracker Account',
        plain_text_content=email_content
    )
    sg.send(message)
    print(f"Activation email sent to {employee['email']}")

# --- API Endpoints ---
@app.route('/employee', methods=['POST'])
def add_employee():
    data_in = request.json
    data = load_data()
    emp = {
        "id": generate_id(),
        "name": data_in["name"],
        "email": data_in["email"],
        "active": False,
        "createdAt": int(time.time() * 1000)
    }
    data['employees'].append(emp)
    save_data(data)
    send_activation_email(emp)
    return jsonify(emp)

@app.route('/employee', methods=['GET'])
def get_employees():
    data = load_data()
    active_only = request.args.get('active', 'false').lower() == 'true'
    if active_only:
        return jsonify([e for e in data['employees'] if e.get('active', False)])
    return jsonify(data['employees'])


@app.route('/project', methods=['POST'])
def add_project():
    data_in = request.json
    data = load_data()
    proj = {
        "id": generate_id(),
        "name": data_in["name"],
        "employeeIds": data_in.get("employeeIds", []),
        "createdAt": int(time.time() * 1000)
    }
    data['projects'].append(proj)

    task = {
        "id": generate_id(),
        "name": f"Default Task for {proj['name']}",
        "projectId": proj['id'],
        "employeeIds": data_in.get("employeeIds", []),
        "createdAt": int(time.time() * 1000)
    }
    data['tasks'].append(task)
    save_data(data)
    return jsonify(proj)

@app.route('/project', methods=['GET'])
def get_projects():
    data = load_data()
    return jsonify(data['projects'])

@app.route('/task', methods=['GET'])
def get_tasks():
    data = load_data()
    return jsonify(data['tasks'])

@app.route('/time', methods=['POST'])
def log_time():
    data_in = request.json
    data = load_data()
    data['timeLogs'].append(data_in)
    save_data(data)
    return jsonify({"status": "Time logged successfully"})

@app.route('/time', methods=['GET'])
def get_time_logs():
    data = load_data()
    return jsonify(data['timeLogs'])

@app.route('/screenshot', methods=['POST'])
def upload_screenshot():
    data_in = request.form
    file = request.files['file']
    employeeId = data_in['employeeId']
    employeeName = data_in['employeeName'].replace(" ", "_")
    projectName = data_in['projectName'].replace(" ", "_")
    timestamp = data_in['timestamp']
    permission = data_in['permission']

    project_dir = os.path.join(SCREENSHOTS_DIR, projectName)
    employee_dir = os.path.join(project_dir, employeeName)
    os.makedirs(employee_dir, exist_ok=True)

    filename = f"{employeeId}_{timestamp}.png"
    filepath = os.path.join(employee_dir, filename)
    file.save(filepath)

    data = load_data()
    data['screenshots'].append({
        "employeeId": employeeId,
        "employeeName": employeeName,
        "projectName": projectName,
        "timestamp": timestamp,
        "permission": permission,
        "filename": filepath
    })
    save_data(data)

    return jsonify({"status": "Screenshot saved"})

@app.route('/screenshot', methods=['GET'])
def get_screenshots():
    data = load_data()
    return jsonify(data['screenshots'])

@app.route('/activate/<emp_id>', methods=['GET'])
def activate_employee(emp_id):
    data = load_data()
    emp = next((e for e in data['employees'] if e['id'] == emp_id), None)
    if emp:
        emp['active'] = True
        save_data(data)
        return f"<h1>Activation Successful!</h1><p>Hi {emp['name']}, you can now download the tracker app: <a href='/static/{TRACKER_APP_FILENAME}'>Download</a></p>"
    else:
        return "<h1>Invalid Activation Link</h1>"

# --- Main Entry Point ---
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

