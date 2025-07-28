import customtkinter as ctk
import os


import requests
import threading
import time
from PIL import ImageGrab
import io
import socket
import uuid
from datetime import datetime


API_BASE = "http://localhost:5000"


def get_network_info():
    ip = socket.gethostbyname(socket.gethostname())
    mac = ':'.join(f'{(uuid.getnode() >> ele) & 0xff:02x}' for ele in range(0,48,8)[::-1])
    return ip, mac


def take_screenshot(emp_id, emp_name, project_name):
    try:
        screenshot = ImageGrab.grab()
        timestamp = datetime.now().isoformat()
        safe_timestamp = timestamp.replace(":", "-").replace(".", "-")


        # Folder Structure: screenshots/ProjectName/EmployeeName/
        folder_path = f"backend/screenshots/{project_name}/{emp_name}"
        os.makedirs(folder_path, exist_ok=True)


        img_bytes = io.BytesIO()
        screenshot.save(img_bytes, format='PNG')
        img_bytes.seek(0)


        files = {'file': ('screenshot.png', img_bytes, 'image/png')}
        data = {
            'employeeId': emp_id,
            'employeeName': emp_name,
            'projectName': project_name,
            'timestamp': safe_timestamp,
            'permission': 'true'
        }


        response = requests.post(f"{API_BASE}/screenshot", files=files, data=data)
        print(f"Screenshot Upload Response: {response.status_code} - {response.text}")


    except Exception as e:
        print(f"Failed to take/upload screenshot: {e}")


def start_tracking(emp_id, emp_name, project_name, task_id, timer_label):
    global tracking, start_time
    tracking = True
    start_time = datetime.now()
    update_timer(timer_label, emp_id, emp_name, project_name, task_id)


def update_timer(label, emp_id, emp_name, project_name, task_id):
    if tracking:
        elapsed = (datetime.now() - start_time).seconds
        label.configure(text=f"Tracking: {elapsed}s")
        if elapsed % 10 == 0:  # Take screenshot every 10 seconds
            take_screenshot(emp_id, emp_name, project_name)
        label.after(1000, update_timer, label, emp_id, emp_name, project_name, task_id)


def stop_tracking(emp_id, emp_name, project_name, task_id):
    global tracking, start_time
    tracking = False
    end_time = datetime.now()
    duration = (end_time - start_time).seconds
    ip, mac = get_network_info()


    payload = {
        "employeeId": emp_id,
        "taskId": task_id,
        "startTime": start_time.isoformat(),
        "endTime": end_time.isoformat(),
        "durationSeconds": duration,
        "ip": ip,
        "mac": mac
    }
    requests.post(f"{API_BASE}/time", json=payload)
    take_screenshot(emp_id, emp_name, project_name)


def main():
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")


    app = ctk.CTk()
    app.title("Time Tracker")
    app.geometry("400x250")


    id_label = ctk.CTkLabel(app, text="Enter your Employee ID:")
    id_label.pack(pady=10)
    id_entry = ctk.CTkEntry(app)
    id_entry.pack(pady=5)


    result_label = ctk.CTkLabel(app, text="")
    result_label.pack(pady=5)


    def verify_and_start():
        emp_id = id_entry.get().strip()
        if not emp_id:
            result_label.configure(text="Please enter a valid Employee ID", text_color="red")
            return


        try:
            employees = requests.get(f"{API_BASE}/employee").json()
            emp_data = next((e for e in employees if e['id'] == emp_id), None)
            if not emp_data:
                result_label.configure(text="Employee ID not found!", text_color="red")
                return
            emp_name = emp_data['name']


            projects = requests.get(f"{API_BASE}/project").json()
            tasks = requests.get(f"{API_BASE}/task").json()


            assigned_projects = [p for p in projects if emp_id in p['employeeIds']]
            if not assigned_projects:
                result_label.configure(text="No projects assigned to this Employee ID", text_color="red")
                return


        except Exception as e:
            result_label.configure(text=f"API Error: {str(e)}", text_color="red")
            return


        # Hide initial inputs
        id_label.pack_forget()
        id_entry.pack_forget()
        verify_button.pack_forget()
        result_label.pack_forget()


        proj_to_task = {p['name']: next((t['id'] for t in tasks if t['projectId'] == p['id']), None) for p in assigned_projects}


        dropdown = ctk.CTkComboBox(app, values=list(proj_to_task.keys()))
        dropdown.pack(pady=10)


        timer_label = ctk.CTkLabel(app, text="Timer: 0s")
        timer_label.pack(pady=10)


        def start_action():
            selected_project_name = dropdown.get()
            threading.Thread(target=start_tracking, args=(emp_id, emp_name, selected_project_name, proj_to_task[selected_project_name], timer_label), daemon=True).start()


        def stop_action():
            selected_project_name = dropdown.get()
            stop_tracking(emp_id, emp_name, selected_project_name, proj_to_task[selected_project_name])


        btn_start = ctk.CTkButton(app, text="Start Tracking", command=start_action)
        btn_stop = ctk.CTkButton(app, text="Stop Tracking", command=stop_action)


        btn_start.pack(pady=5)
        btn_stop.pack(pady=5)


    verify_button = ctk.CTkButton(app, text="Proceed", command=verify_and_start)
    verify_button.pack(pady=5)


    app.mainloop()


if __name__ == "__main__":
    main()
