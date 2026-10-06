### Hospital Management System – MAD-I Project

This application is developed as a course project for **Modern Application Development – I**.  
It manages the workflow between Admin, Doctors, and Patients by providing a clean and functional web interface.


##  Project Overview

The system focuses on organizing hospital operations digitally.   
It includes doctor management, patient registration, appointment scheduling, treatment recording, and dashboards for each role.  
Both backend logic and UI have been built using Flask, SQLAlchemy, HTML, CSS, and JavaScript (Chart.js).



## Tech Stack

**Backend**
- Python 3  
- Flask Framework  
- Flask-Login  
- SQLAlchemy ORM  
- SQLite Database  

**Frontend**
- HTML5  
- Bootstrap  
- CSS  
- JavaScript (Chart.js)


##  User Roles and Permissions

### **Admin**
- Add doctors and departments  
- View all doctors, patients, and appointments  
- Manage hospital-wide statistics  
- Access patient history  
- Full control over system data  

### **Doctor**
- View assigned appointments  
- Update appointment status  
- Add diagnosis, treatment, and prescriptions  
- Review patient history  

### **Patient**
- Register an account  
- Book, reschedule, or cancel appointments  
- Search doctors by name or department  
- View upcoming and previous visits  


##  Directory Structure

Hospital Management/
│
├── app.py # Main Flask application
├── requirements.txt # Python dependencies
├── readme.md # Project documentation
├── .gitignore # Git ignore rules
│
├── instance/
│ └── hms_database.db # SQLite database (auto-generated)
│
├── static/
│ └── style.css # Custom CSS for UI styling
│
└── templates/
├── base.html
├── login.html
├── registration.html
├── admin_dashboard.html
├── admin_patient_history.html
├── add_department.html
├── add_doctor.html
├── doctor_dashboard.html
├── patient_dashboard.html
├── book_appointment.html
├── complete_visit.html
├── patient_history.html
└── search_doctor.html


## HMS_Project Video presentation:-
https://drive.google.com/file/d/1G7XOMhfsbpA7DwiELZAxADO0x7nzcSaR/view?usp=sharing