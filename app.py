from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time

app = Flask(__name__)
app.secret_key = "HMS_SECRET_2025"

# SQLite Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hms_database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "user_signin"


# ---------------------- DATABASE MODELS ----------------------

class Department(db.Model):
    __tablename__ = "departments"

    dept_id = db.Column(db.Integer, primary_key=True)
    dept_name = db.Column(db.String(100), unique=True, nullable=False)
    dept_description = db.Column(db.Text)

    assigned_doctors = db.relationship("UserAccount", backref="department_link")


class UserAccount(db.Model, UserMixin):

    __tablename__ = "user_accounts"

    user_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False, unique=True)
    login_password = db.Column(db.String(120), nullable=False)
    contact_email = db.Column(db.String(150), unique=True)

    user_role = db.Column(db.String(20))  # admin, doctor, patient
    joined_on = db.Column(db.DateTime, default=datetime.utcnow)

    dept_reference = db.Column(db.Integer, db.ForeignKey("departments.dept_id"))

    patient_visits = db.relationship("DoctorAppointment", foreign_keys='DoctorAppointment.patient_ref', backref='patient')
    doctor_schedule = db.relationship("DoctorAppointment", foreign_keys='DoctorAppointment.doctor_ref', backref='doctor')

    # Flask-Login expects get_id() to return a str id; default UserMixin expects 'id' attribute.
    # Our primary key is user_id, so implement get_id:
    def get_id(self):
        return str(self.user_id)


class DoctorAppointment(db.Model):
    __tablename__ = "doctor_appointments"

    appt_id = db.Column(db.Integer, primary_key=True)
    visit_date = db.Column(db.Date, nullable=False)
    visit_time = db.Column(db.Time, nullable=False)

    appt_status = db.Column(db.String(50), default="Booked")

    patient_ref = db.Column(db.Integer, db.ForeignKey("user_accounts.user_id"))
    doctor_ref = db.Column(db.Integer, db.ForeignKey("user_accounts.user_id"))

    care_report = db.relationship("PatientTreatment", backref="appointment_info", uselist=False)


class PatientTreatment(db.Model):
    __tablename__ = "patient_treatments"

    report_id = db.Column(db.Integer, primary_key=True)
    medical_issue = db.Column(db.String(255))
    medicine_prescribed = db.Column(db.Text)
    doctor_observation = db.Column(db.Text)

    appointment_ref = db.Column(db.Integer, db.ForeignKey("doctor_appointments.appt_id"))


# ------------------ Flask-Login user loader ------------------

@login_manager.user_loader
def load_user(user_id):
    try:
        return UserAccount.query.get(int(user_id))
    except Exception:
        return None


# ---------------------- ROUTES ----------------------

@app.route("/")
def home_page():
    return render_template("base.html")


@app.route("/signin", methods=["GET", "POST"])
def user_signin():

    if request.method == "POST":

        userid = request.form.get("username", "").strip()
        passwd = request.form.get("password", "").strip()

        # ---------- BACKEND VALIDATION ----------
        if not userid or len(userid) < 3:
            flash("Username must be at least 3 characters long.", "error")
            return redirect("/signin")

        if not passwd or len(passwd) < 4:
            flash("Password must be at least 4 characters long.", "error")
            return redirect("/signin")
        # ----------------------------------------

        # lookup in database
        user = UserAccount.query.filter_by(
            full_name=userid,
            login_password=passwd
        ).first()

        if not user:
            flash("Invalid username or password.", "error")
            return redirect("/signin")

        # set login via Flask-Login and keep session entries for compatibility with existing code
        login_user(user)
        session["active_user"] = user.user_id
        session["active_role"] = user.user_role

        # redirect based on role
        if user.user_role == "admin":
            return redirect("/admin-panel")
        elif user.user_role == "doctor":
            return redirect("/doctor-panel")
        else:
            return redirect("/patient-panel")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def patient_signup():
    if request.method == "POST":
        uname = request.form["username"].strip()
        mail = request.form["email"].strip()
        pwd = request.form["password"].strip()

        # Empty Check
        if len(uname) < 3:
            flash("Name must be at least 3 characters.", "error")
            return redirect("/signup")

        if "@" not in mail or "." not in mail:
            flash("Invalid email format.", "error")
            return redirect("/signup")

        if len(pwd) < 5:
            flash("Password must be at least 5 characters.", "error")
            return redirect("/signup")

        # Duplicate Email Check
        if UserAccount.query.filter_by(contact_email=mail).first():
            flash("Email already registered!", "error")
            return redirect("/signup")

        # Duplicate Username Check
        if UserAccount.query.filter_by(full_name=uname).first():
            flash("Username already exists!", "error")
            return redirect("/signup")

        new_patient = UserAccount(
            full_name=uname,
            contact_email=mail,
            login_password=pwd,
            user_role="patient"
        )
        db.session.add(new_patient)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect("/signin")

    return render_template("registration.html")


# Admin panel: ensure user is authenticated and is admin
@app.route("/admin-panel")
@login_required
def admin_panel():

    if current_user.user_role != "admin":
        flash("Access denied.", "error")
        return redirect("/signin")

    doctors = UserAccount.query.filter_by(user_role="doctor").all()
    patients = UserAccount.query.filter_by(user_role="patient").all()
    appointments = DoctorAppointment.query.all()
    departments = Department.query.all()

    stats = {
        "doctor_count": len(doctors),
        "patient_count": len(patients),
        "appointment_count": len(appointments),
        "department_count": len(departments)
    }

    return render_template(
        "admin_dashboard.html",
        doctors=doctors,
        patients=patients,
        appointments=appointments,
        departments=departments,
        stats=stats
    )


@app.route("/doctor-panel")
@login_required
def doctor_panel():

    # must be doctor
    if current_user.user_role != "doctor":
        flash("Access denied.", "error")
        return redirect("/signin")

    doc_id = current_user.user_id
    appointments = DoctorAppointment.query.filter_by(doctor_ref=doc_id).all()

    completed = DoctorAppointment.query.filter_by(doctor_ref=doc_id, appt_status="Completed").count()
    pending = DoctorAppointment.query.filter_by(doctor_ref=doc_id, appt_status="Booked").count()
    cancelled = DoctorAppointment.query.filter_by(doctor_ref=doc_id, appt_status="Cancelled").count()

    return render_template(
        "doctor_dashboard.html",
        appointments=appointments,
        completed_count=completed,
        pending_count=pending,
        cancelled_count=cancelled
    )


@app.route("/patient-panel")
@login_required
def patient_panel():

    # must be patient
    if current_user.user_role != "patient":
        flash("Access denied.", "error")
        return redirect("/signin")

    uid = current_user.user_id

    visits = DoctorAppointment.query.filter_by(patient_ref=uid).all()

    completed = DoctorAppointment.query.filter_by(patient_ref=uid, appt_status="Completed").count()
    upcoming = DoctorAppointment.query.filter(
        DoctorAppointment.patient_ref == uid,
        DoctorAppointment.appt_status != "Completed"
    ).count()

    total = len(visits)

    return render_template(
        "patient_dashboard.html",
        visits=visits,
        completed_visits=completed,
        upcoming_visits=upcoming,
        total_visits=total
    )


@app.route("/logout")
@login_required
def user_logout():
    # clear both Flask-Login session and legacy session keys
    try:
        logout_user()
    except Exception:
        pass

    session.pop("active_user", None)
    session.pop("active_role", None)
    return redirect(url_for("user_signin"))


@app.route('/add-doctor', methods=['GET', 'POST'])
@login_required
def add_doctor():

    # Only admin can access this page
    if current_user.user_role != "admin":
        flash("Access denied.", "error")
        return redirect("/signin")

    departments = Department.query.all()

    if request.method == 'POST':

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        dept = request.form.get("department")

        # ---------------------------------------------------
        #                BACKEND VALIDATION
        # ---------------------------------------------------

        # Empty fields
        if not name or not email or not password or not dept:
            flash("All fields are required.", "error")
            return redirect("/add-doctor")

        # Name validation
        if len(name) < 3:
            flash("Doctor name must be at least 3 characters.", "error")
            return redirect("/add-doctor")

        # Email format check
        if "@" not in email or "." not in email:
            flash("Please enter a valid email address.", "error")
            return redirect("/add-doctor")

        # Password length validation
        if len(password) < 5:
            flash("Password must be minimum 5 characters long.", "error")
            return redirect("/add-doctor")

        # Department selection
        if dept == "" or dept is None:
            flash("Please select a department.", "error")
            return redirect("/add-doctor")

        # Check: email must not exist
        if UserAccount.query.filter_by(contact_email=email).first():
            flash("Email already registered. Try another.", "error")
            return redirect("/add-doctor")

        # Check: doctor name must not exist
        if UserAccount.query.filter_by(full_name=name).first():
            flash("Doctor name already exists.", "error")
            return redirect("/add-doctor")

        # ---------------------------------------------------
        #              CREATE NEW DOCTOR AFTER VALIDATION
        # ---------------------------------------------------

        new_doc = UserAccount(
            full_name=name,
            contact_email=email,
            login_password=password,
            user_role="doctor",
            dept_reference=dept
        )

        db.session.add(new_doc)
        db.session.commit()

        flash("Doctor added successfully!", "success")
        return redirect("/admin-panel")

    # GET Request
    return render_template('add_doctor.html', departments=departments)

@app.route("/add-department-page")
@login_required
def add_department_page():

    if current_user.user_role != "admin":
        flash("Access denied.", "error")
        return redirect("/signin")

    return render_template("add_department.html")


@app.route("/add-department", methods=["POST"])
@login_required
def add_department():

    if current_user.user_role != "admin":
        flash("Access denied.", "error")
        return redirect("/signin")

    newdept = Department(
        dept_name=request.form["deptname"],
        dept_description=request.form["desc"]
    )
    db.session.add(newdept)
    db.session.commit()

    return redirect("/admin-panel")


@app.route("/book", methods=["GET", "POST"])
@login_required
def book_appointment():

    if current_user.user_role != "patient":
        flash("Access denied.", "error")
        return redirect("/signin")

    all_doctors = UserAccount.query.filter_by(user_role="doctor").all()

    if request.method == "POST":

        doc = request.form.get("doctor")
        d = request.form.get("date")
        t = request.form.get("time")

        # ---------------- VALIDATION ----------------

        if not doc:
            flash("Please select a doctor.", "error")
            return redirect("/book")

        if not d:
            flash("Please choose a date.", "error")
            return redirect("/book")

        if not t:
            flash("Please choose a time.", "error")
            return redirect("/book")

        # Convert string to proper Python date & time
        try:
            selected_date = datetime.strptime(d, "%Y-%m-%d").date()
            selected_time = datetime.strptime(t, "%H:%M").time()
        except:
            flash("Invalid date or time format.", "error")
            return redirect("/book")

        # Prevent past dates
        if selected_date < datetime.now().date():
            flash("Cannot book a past date.", "error")
            return redirect("/book")

        # Conflict check
        clash = DoctorAppointment.query.filter_by(
            doctor_ref=int(doc),
            visit_date=selected_date,
            visit_time=selected_time
        ).first()

        if clash:
            flash("Doctor already booked at this time.", "error")
            return redirect("/book")

        # ---------------- SAVE TO DATABASE ----------------
        new_apt = DoctorAppointment(
            visit_date=selected_date,
            visit_time=selected_time,
            patient_ref=current_user.user_id,
            doctor_ref=int(doc)
        )

        db.session.add(new_apt)
        db.session.commit()

        flash("Appointment booked successfully", "success")
        return redirect("/patient-panel")

    return render_template("book_appointment.html", doctors=all_doctors)



@app.route("/complete/<int:aid>", methods=["POST"])
@login_required
def complete_appt(aid):

    # only doctor allowed to complete (or admin)
    if current_user.user_role not in ("doctor", "admin"):
        flash("Access denied.", "error")
        return redirect("/signin")

    appt = DoctorAppointment.query.get(aid)

    report = PatientTreatment(
        appointment_ref=aid,
        medical_issue=request.form["issue"],
        medicine_prescribed=request.form["medicine"],
        doctor_observation=request.form["note"]
    )

    appt.appt_status = "Completed"

    db.session.add(report)
    db.session.commit()

    return redirect("/doctor-panel")


@app.route("/close-visit/<int:apt_id>", methods=["POST"])
@login_required
def close_visit(apt_id):

    # doctor role check
    if current_user.user_role != "doctor":
        flash("Access denied.", "error")
        return redirect("/signin")

    booking = DoctorAppointment.query.get(apt_id)

    # appointment exist check
    if not booking:
        return redirect("/doctor-panel")

    # treatment create
    record = PatientTreatment(
        appointment_ref=apt_id,
        medical_issue=request.form.get("symptom_box"),
        medicine_prescribed=request.form.get("drug_box"),
        doctor_observation=request.form.get("note_box")
    )

    booking.appt_status = "Completed"

    db.session.add(record)
    db.session.commit()

    return redirect("/doctor-panel")


@app.route("/remove-visit/<int:apt_id>")
@login_required
def remove_visit(apt_id):

    if current_user.user_role != "doctor":
        flash("Access denied.", "error")
        return redirect("/signin")

    visit = DoctorAppointment.query.get(apt_id)

    if visit:
        visit.appt_status = "Cancelled"
        db.session.commit()

    return redirect("/doctor-panel")


@app.route("/patient-history/<int:pid>")
@login_required
def patient_history(pid):

    if current_user.user_role != "doctor":
        flash("Access denied.", "error")
        return redirect("/signin")

    all_visits = DoctorAppointment.query.filter_by(patient_ref=pid).all()

    return render_template("patient_history.html", visits=all_visits)


@app.route("/find-doctor", methods=["POST"])
@login_required
def find_doctor():

    if current_user.user_role != "patient":
        flash("Access denied.", "error")
        return redirect("/signin")

    keyword = request.form["keyword"]

    result = UserAccount.query.filter(
        UserAccount.user_role == "doctor",
        UserAccount.full_name.ilike(f"%{keyword}%")
    ).all()

    return render_template("search_doctor.html", doctors=result, keyword=keyword)


@app.route("/reschedule/<int:apt_id>", methods=["POST"])
@login_required
def reschedule_visit(apt_id):

    if current_user.user_role != "patient":
        flash("Access denied.", "error")
        return redirect("/signin")

    visit = DoctorAppointment.query.get(apt_id)

    new_date = request.form["new_date"]
    new_time = request.form["new_time"]

    # Conflict check
    clash = DoctorAppointment.query.filter_by(
        doctor_ref=visit.doctor_ref,
        visit_date=new_date,
        visit_time=new_time
    ).first()

    if clash:
        flash("Doctor is already booked for this time.", "error")
    else:
        visit.visit_date = new_date
        visit.visit_time = new_time
        db.session.commit()

        flash("Appointment rescheduled.", "success")

    return redirect("/patient-panel")


@app.route("/cancel/<int:apt_id>")
@login_required
def cancel_appointment(apt_id):

    if current_user.user_role != "patient":
        flash("Access denied.", "error")
        return redirect("/signin")

    visit = DoctorAppointment.query.get(apt_id)

    if visit:
        visit.appt_status = "Cancelled"
        db.session.commit()

    return redirect("/patient-panel")


@app.route("/admin/history/<int:pid>")
@login_required
def admin_patient_history(pid):

    if current_user.user_role != "admin":
        flash("Access denied.", "error")
        return redirect("/signin")

    visits = DoctorAppointment.query.filter_by(patient_ref=pid).all()

    return render_template("admin_patient_history.html", visits=visits)


# ---------------------- APIs ----------------------

@app.route("/api/doctors")
@login_required
def api_fetch_doctors():

    # auth: allow admin/doctor/patient to fetch doctors (or tighten if needed)
    doctors = UserAccount.query.filter_by(user_role="doctor").all()

    data = [
        {
            "id": d.user_id,
            "name": d.full_name,
            "email": d.contact_email,
            "department": d.department_link.dept_name if d.department_link else None
        }
        for d in doctors
    ]

    return jsonify({"status": "success", "doctors": data})


@app.route("/api/department", methods=["POST"])
@login_required
def api_create_department():

    # only admin can create departments
    if current_user.user_role != "admin":
        return jsonify({"status": "error", "message": "Unauthorized"}), 401

    body = request.get_json() or {}

    new_dept = Department(
        dept_name=body.get("name"),
        dept_description=body.get("description")
    )

    db.session.add(new_dept)
    db.session.commit()

    return jsonify({"status": "success", "message": "Department added"})


@app.route("/api/appointment/<int:aid>", methods=["PUT"])
@login_required
def api_update_appointment(aid):

    data = request.get_json() or {}
    appt = DoctorAppointment.query.get(aid)

    if not appt:
        return jsonify({"status": "error", "message": "Appointment not found"}), 404

    # conflict check
    doctor = appt.doctor_ref
    new_date = data.get("date")
    new_time = data.get("time")

    conflict = DoctorAppointment.query.filter_by(
        doctor_ref=doctor,
        visit_date=new_date,
        visit_time=new_time
    ).first()

    if conflict:
        return jsonify({"status": "error", "message": "Doctor not available at that time"}), 409

    appt.visit_date = new_date
    appt.visit_time = new_time

    db.session.commit()

    return jsonify({"status": "success", "message": "Appointment rescheduled"})


@app.route("/api/appointment/<int:aid>", methods=["DELETE"])
@login_required
def api_delete_appointment(aid):

    appt = DoctorAppointment.query.get(aid)

    if not appt:
        return jsonify({"status": "error", "message": "Not found"}), 404

    db.session.delete(appt)
    db.session.commit()

    return jsonify({"status": "success", "message": "Appointment removed"})


# ---------------------- DATABASE INIT + ADMIN CREATION ----------------------

if __name__ == "__main__":
    with app.app_context():
        db.create_all()

        admin_user = UserAccount.query.filter_by(full_name="admin").first()

        if not admin_user:
            admin_account = UserAccount(
                full_name="admin",
                contact_email="admin.hms@hospital.com",
                login_password="admin@123",
                user_role="admin"
            )
            db.session.add(admin_account)
            db.session.commit()

    app.run(debug=True, use_reloader=True)
