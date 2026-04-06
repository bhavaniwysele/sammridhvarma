import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.upcoming_events_models import Event, Registration
from app.schemas.upcoming_events_schemas import RegistrationCreate
from app.utils.email_upcoming_events import send_email
from app.s3 import upload_to_s3
from datetime import datetime

router = APIRouter(prefix="/UpcomingEvents", tags=["UpcomingEvents"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")


def parse_time(time_str):
    for fmt in ["%H:%M:%S", "%H:%M", "%I:%M%p", "%I:%M %p"]:
        try:
            return datetime.strptime(time_str.strip(), fmt).time()
        except Exception:
            continue
    raise ValueError("Invalid time format")


def verify_google_token(token: str) -> dict:
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests
    try:
        # Accept both your client ID and OAuth Playground client ID (for testing)
        valid_audiences = [GOOGLE_CLIENT_ID, "407408718192.apps.googleusercontent.com"]
        for audience in valid_audiences:
            try:
                return id_token.verify_oauth2_token(token, google_requests.Request(), audience)
            except Exception:
                continue
        raise Exception("Token verification failed for all audiences")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")


# STEP 1: Frontend sends Google token → backend verifies → returns email
@router.post("/verify-google-token")
def verify_token(data: dict):
    token = data.get("token") or data.get("id_token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    idinfo = verify_google_token(token)
    return {
        "verified": True,
        "email": idinfo["email"],
        "name": idinfo.get("name")
    }


# CREATE EVENT (admin)
@router.post("/create")
def create_event(
    title: str = Form(..., description="Event title"),
    description: str = Form(..., description="Event description"),
    event_date: str = Form(..., description="Date in DD-MM-YYYY format"),
    start_time: str = Form(..., description="Start time e.g. 10:00"),
    end_time: str = Form(..., description="End time e.g. 13:00"),
    location: str = Form(..., description="Event venue"),
    image: UploadFile = File(..., description="Event image"),
    db: Session = Depends(get_db)
):
    try:
        event_date_obj = datetime.strptime(event_date, "%d-%m-%Y").date()
        start_time_obj = parse_time(start_time)
        end_time_obj = parse_time(end_time)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    image_url = upload_to_s3(image)

    new_event = Event(
        title=title,
        description=description,
        event_date=event_date_obj,
        start_time=start_time_obj,
        end_time=end_time_obj,
        location=location,
        image_url=image_url
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)
    return {"event_id": new_event.id, "message": "Event created successfully"}

# STEP 2: User fills form and submits with verified email
@router.post("/register")
def register_user(
    data: RegistrationCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    email = data.email

    event = db.query(Event).filter(Event.id == data.event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    existing = db.query(Registration).filter(
        Registration.email == email,
        Registration.event_id == data.event_id
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already registered for this event")

    new_reg = Registration(
        event_id=data.event_id,
        full_name=data.full_name,
        phone=data.phone,
        email=email,
        city=data.city,
        source=data.source,
        other_source=data.other_source
    )
    db.add(new_reg)
    db.commit()

    subject = f"Registration Confirmed - {event.title}"
    body = f"""Dear {data.full_name},

Thank you for registering! Your registration has been confirmed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EVENT DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Event  : {event.title}
 Date   : {event.event_date}
 Time   : {event.start_time} - {event.end_time}
 Venue  : {event.location}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 YOUR REGISTRATION DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Name   : {data.full_name}
 Email  : {email}
 Phone  : {data.phone}
 City   : {data.city}
 Source : {data.source}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

We look forward to seeing you at the event.
For any queries, please reply to this email.

Warm regards,
Sammridhvarma Team"""

    ADMIN_EMAIL = os.environ.get("SMTP_EMAIL")
    recipients = [email]
    if ADMIN_EMAIL and ADMIN_EMAIL != email:
        recipients.append(ADMIN_EMAIL)

    background_tasks.add_task(send_email, recipients, subject, body)
    return {"message": "Registered successfully"}

# GET ALL EVENTS
@router.get("/")
def get_events(db: Session = Depends(get_db)):
    return db.query(Event).all()

# UPDATE EVENT
@router.put("/{id}")
def update_event(
    id: int,
    title: str = Form(None),
    description: str = Form(None),
    event_date: str = Form(None, description="DD-MM-YYYY"),
    start_time: str = Form(None),
    end_time: str = Form(None),
    location: str = Form(None),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    def is_valid(v):
        return v and v.strip() != "" and v != "string"

    if is_valid(title):
        event.title = title
    if is_valid(description):
        event.description = description
    if is_valid(location):
        event.location = location
    if is_valid(event_date):
        try:
            event.event_date = datetime.strptime(event_date, "%d-%m-%Y").date()
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid date format. Use DD-MM-YYYY")
    if is_valid(start_time):
        try:
            event.start_time = parse_time(start_time)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid start time")
    if is_valid(end_time):
        try:
            event.end_time = parse_time(end_time)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid end time")
    if image and image.filename and image.filename.strip() != "":
        event.image_url = upload_to_s3(image)

    db.commit()
    db.refresh(event)
    return {"message": "Event updated successfully", "event_id": event.id}


# DELETE EVENT
@router.delete("/{id}")
def delete_event(id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    db.query(Registration).filter(Registration.event_id == id).delete()
    db.delete(event)
    db.commit()
    return {"message": "Event deleted successfully"}


# GET REGISTRATIONS FOR AN EVENT (admin)
@router.get("/{id}/registrations")
def get_registrations(id: int, db: Session = Depends(get_db)):
    event = db.query(Event).filter(Event.id == id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db.query(Registration).filter(Registration.event_id == id).all()
