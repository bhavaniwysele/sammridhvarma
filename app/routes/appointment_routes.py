from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.appointments import Appointment
import shutil, os, re
from datetime import datetime


router = APIRouter(prefix="/appointment", tags=["Appointment"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ✅ Create Appointment
@router.post("/appointments")
def create_appointment(
    full_name: str = Form(...),

    mobile_number: str = Form(...),

    email: str = Form(None),

    district: str = Form(None),
    village: str = Form(None),

    constituency: str = Form(...),
    preferred_date: str = Form(...),
    time_slot: str = Form(...),
    issue_category: str = Form(None),

    subject: str = Form(...),
    description: str = Form(...),

    file: UploadFile = File(None),

    db: Session = Depends(get_db)
):
    if not mobile_number.isdigit() or len(mobile_number) != 10:
        raise HTTPException(status_code=422, detail="Phone number must be exactly 10 digits")

    if email and not re.match(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$", email):
        raise HTTPException(status_code=422, detail="Invalid email address")

    # Safe date parsing
    try:
        parsed_date = datetime.strptime(preferred_date, "%d-%m-%Y").date()
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid date format. Use DD-MM-YYYY")

    # ✅ Prevent duplicate booking
    existing = db.query(Appointment).filter(
        Appointment.mobile_number == mobile_number,
        Appointment.preferred_date == parsed_date,
        Appointment.time_slot == time_slot
    ).first()

    if existing:
        raise HTTPException(status_code=409, detail="You already booked this slot")

    # ✅ File upload handling
    file_path = None
    if file and file.filename and file.filename.strip() != "":
        unique_name = f"{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    # ✅ Save to DB
    new_appointment = Appointment(
        full_name=full_name,
        mobile_number=mobile_number,
        email=email,
        district=district,
        village=village,
        constituency=constituency,
        preferred_date=parsed_date,
        time_slot=time_slot,
        issue_category=issue_category,
        subject=subject,
        description=description,
        document=file_path,
        status="pending"
    )

    db.add(new_appointment)
    db.commit()
    db.refresh(new_appointment)

    return {
        "message": "Appointment Created Successfully",
        "id": new_appointment.id
    }


# ✅ Get all appointments (with optional status filter)
@router.get("/appointments")
def get_appointments(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Appointment)

    if status:
        query = query.filter(Appointment.status == status)

    return query.all()


# ✅ Update status (Approve / Reject)
@router.put("/appointments/{id}")
def update_status(id: int, status: str, db: Session = Depends(get_db)):
    appointment = db.query(Appointment).filter(Appointment.id == id).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    appointment.status = status
    db.commit()

    return {"message": "Status Updated"}