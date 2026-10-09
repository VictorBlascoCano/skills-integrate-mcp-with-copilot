"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import hashlib
import hmac
import json
import secrets
import time
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
TEACHER_FILE = current_dir / "teachers.json"
SESSION_TTL_SECONDS = 8 * 60 * 60
sessions = {}
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")


class TeacherCredentials(BaseModel):
    username: str
    password: str


def load_teachers():
    try:
        with TEACHER_FILE.open(encoding="utf-8") as teacher_file:
            data = json.load(teacher_file)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail="Teacher login is not configured. Ask an administrator to add a teacher account.",
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="Teacher login is unavailable because its configuration could not be read.",
        ) from exc

    if not isinstance(data, dict) or not isinstance(data.get("teachers"), list):
        raise HTTPException(
            status_code=503,
            detail="Teacher login configuration is invalid.",
        )
    return data["teachers"]


def verify_password(password, teacher):
    try:
        salt = bytes.fromhex(teacher["salt"])
        expected_hash = bytes.fromhex(teacher["password_hash"])
        iterations = int(teacher["iterations"])
    except (KeyError, TypeError, ValueError):
        return False

    actual_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual_hash, expected_hash)


def require_teacher(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Teacher login required")

    token = authorization.removeprefix("Bearer ")
    session = sessions.get(token)
    if session is None:
        raise HTTPException(status_code=401, detail="Teacher login required")

    username, expires_at = session
    if expires_at <= time.monotonic():
        sessions.pop(token, None)
        raise HTTPException(status_code=401, detail="Teacher session expired")
    return username


@app.post("/auth/login")
def teacher_login(credentials: TeacherCredentials):
    teachers = load_teachers()
    teacher = next(
        (
            account
            for account in teachers
            if isinstance(account, dict)
            and account.get("username") == credentials.username
        ),
        None,
    )
    if teacher is None or not verify_password(credentials.password, teacher):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    token = secrets.token_urlsafe(32)
    sessions[token] = (credentials.username, time.monotonic() + SESSION_TTL_SECONDS)
    return {"access_token": token, "token_type": "bearer", "username": credentials.username}


@app.get("/auth/session")
def get_teacher_session(username: str = Depends(require_teacher)):
    return {"username": username}


@app.post("/auth/logout")
def teacher_logout(
    authorization: str | None = Header(default=None),
    username: str = Depends(require_teacher),
):
    token = authorization.removeprefix("Bearer ")
    sessions.pop(token, None)
    return {"message": f"Signed out {username}"}

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(
    activity_name: str,
    email: str,
    username: str = Depends(require_teacher),
):
    """Sign up a student for an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is not already signed up
    if email in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is already signed up"
        )

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(
    activity_name: str,
    email: str,
    username: str = Depends(require_teacher),
):
    """Unregister a student from an activity"""
    # Validate activity exists
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Validate student is signed up
    if email not in activity["participants"]:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity"
        )

    # Remove student
    activity["participants"].remove(email)
    return {"message": f"Unregistered {email} from {activity_name}"}
