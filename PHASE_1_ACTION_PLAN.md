# Refactoring Action Plan - Step by Step
**Created**: February 11, 2026  
**Target Timeline**: 8-12 weeks  
**Current Phase**: 0 (Planning Complete - Ready to Start)

---

## 🎯 Before You Begin: Decision Checklist

**Answer these 6 questions first** (takes 30 minutes):

### Question 1: LLM Strategy
- **Decision**: Will you stick with GPT-4o-mini only, or support multiple LLMs?
  - Option A: GPT-4o-mini only (simpler, stick with current)
  - Option B: Support multiple (GPT, Claude, Gemini)
  - Option C: Support local models too (Ollama, LLaMA)
- **Recommendation for MVP**: Option A (GPT-4o-mini) - you can add others later
- **My advice**: Choose A for Phase 1, plan for B in Phase 3

### Question 2: Transcription Services
- **Decision**: Keep Whisper only or add alternatives?
  - Option A: Whisper only (current, good for all languages)
  - Option B: Add Deepgram (faster, better pricing)
  - Option C: Add AssemblyAI (AI-powered features)
- **Recommendation for MVP**: Option A (Whisper)
- **My advice**: Stick with Whisper, it works well

### Question 3: Database Type
- **Decision**: Where to store meetings and settings?
  - Option A: SQLite (local, no external dependencies)
  - Option B: PostgreSQL (scalable, cloud-ready)
  - Option C: Firebase (serverless, simpler ops)
- **Recommendation for MVP**: Option A (SQLite)
- **My advice**: Start with SQLite. You can migrate to PostgreSQL later if needed

### Question 4: User Management
- **Decision**: Single user or multi-user support?
  - Option A: Single user only (current local use)
  - Option B: Multi-user with login (future cloud)
  - Option C: Multi-workspace (teams)
- **Recommendation for MVP**: Option A (single user)
- **My advice**: Design for multi-user in database but don't implement auth yet

### Question 5: Mobile Strategy
- **Decision**: What type of mobile support?
  - Option A: PWA only (web app on home screen, fastest)
  - Option B: React Native (cross-platform native, 3-4 weeks)
  - Option C: Native iOS/Android (highest quality, longest)
- **Recommendation for MVP**: Option A (PWA)
- **My advice**: Start with PWA, graduate to React Native if needed

### Question 6: Email Export Service
- **Decision**: How to send emails?
  - Option A: No email initially (skip for Phase 1)
  - Option B: Self-hosted SMTP (if you have a server)
  - Option C: SendGrid/Mailgun (free tier available)
- **Recommendation for MVP**: Option C (SendGrid free tier)
- **My advice**: Skip email for Phase 1, add it in Phase 3

---

## 📋 Step-by-Step Action Plan

### STEP 1: Make Decisions (Day 1 - 30 min)

**Action**: Answer the 6 questions above and document your choices

**Deliverable**: A simple text file or note with your answers

**Example**:
```
Decision Log:
1. LLM: GPT-4o-mini only (add others later)
2. Transcription: Whisper only
3. Database: SQLite
4. Users: Single user (design for multi later)
5. Mobile: PWA first, React Native later
6. Email: Skip for Phase 1, add in Phase 3
```

---

### STEP 2: Set Up Project Structure (Day 1 - 1 hour)

**Action**: Create new folder structure WITHOUT modifying existing code

**Commands** (run these):
```bash
# From /Users/delaneroberts/meeting_assistant/

# Create backend directories
mkdir -p backend/services
mkdir -p backend/routes
mkdir -p tests

# Create frontend directories
mkdir -p frontend/js
mkdir -p frontend/css

# Create migration directory
mkdir -p migrations

# Create documentation directory
mkdir -p docs

# Current files stay as-is:
# - app.py (will refactor later)
# - static/script.js (will split later)
# - templates/index.html (will keep)
```

**Structure after this step**:
```
meeting_assistant/
├── app.py                    # KEEP AS IS (temporary)
├── static/                   # KEEP AS IS (temporary)
├── templates/                # KEEP AS IS (temporary)
├── backend/                  # NEW
│   ├── __init__.py
│   ├── config.py             # Create (empty for now)
│   ├── services/             # NEW
│   │   ├── __init__.py
│   │   ├── transcription.py  # Extract from app.py
│   │   ├── translation.py    # Extract from app.py
│   │   ├── summarization.py  # Extract from app.py
│   │   ├── export.py         # Create new
│   │   └── qa_detection.py   # Extract from app.py
│   ├── routes/               # NEW
│   │   ├── __init__.py
│   │   ├── api.py            # Create new
│   │   ├── settings.py       # Create new
│   │   └── export.py         # Create new
│   └── models.py             # Create new
├── frontend/                 # NEW
│   ├── js/                   # NEW (will split script.js here)
│   └── css/                  # NEW
├── tests/                    # NEW
│   ├── __init__.py
│   ├── test_services.py      # Create
│   └── test_api.py           # Create
├── migrations/               # NEW (for database)
├── docs/                     # NEW
└── [keep all existing files]
```

**Deliverable**: New folder structure created, no code changes yet

---

### STEP 3: Create Database Schema (Day 2 - 2 hours)

**Action**: Create `backend/models.py` with database models

**Create file**: `backend/models.py`

```python
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Meeting(db.Model):
    """Store meeting data"""
    __tablename__ = 'meetings'
    
    id = db.Column(db.String(36), primary_key=True)  # UUID
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Audio info
    audio_filename = db.Column(db.String(256))
    audio_path = db.Column(db.String(512))
    original_language = db.Column(db.String(50))
    
    # Content
    transcript_original = db.Column(db.Text)
    transcript_english = db.Column(db.Text)
    summary_original = db.Column(db.Text)
    summary_english = db.Column(db.Text)
    action_items = db.Column(db.JSON)  # Store as JSON array
    
    # Metadata
    metadata = db.Column(db.JSON)  # {agenda: "", attendees: "", etc}
    
    # Export history relationship
    exports = db.relationship('ExportHistory', backref='meeting', lazy=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'original_language': self.original_language,
            'summary': self.summary_original,
            'transcript': self.transcript_original,
            'action_items': self.action_items,
        }

class Setting(db.Model):
    """Store admin settings"""
    __tablename__ = 'settings'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True)
    value = db.Column(db.String(512))
    data_type = db.Column(db.String(20))  # 'string', 'json', 'bool'
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @staticmethod
    def get(key, default=None):
        setting = Setting.query.filter_by(key=key).first()
        return setting.value if setting else default
    
    @staticmethod
    def set(key, value, data_type='string'):
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            setting.value = str(value)
            setting.data_type = data_type
        else:
            setting = Setting(key=key, value=str(value), data_type=data_type)
        db.session.add(setting)
        db.session.commit()

class ExportHistory(db.Model):
    """Track exports"""
    __tablename__ = 'export_history'
    
    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.String(36), db.ForeignKey('meetings.id'), nullable=False)
    export_type = db.Column(db.String(50))  # 'email', 'file', 'pdf'
    recipient = db.Column(db.String(256))  # Email or filepath
    status = db.Column(db.String(20))  # 'success', 'failed'
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

**Deliverable**: `backend/models.py` with 3 tables defined

---

### STEP 4: Extract Services from Current app.py (Day 2-3 - 4 hours)

**Action**: Copy relevant functions from `app.py` into new service modules

**Create files**:

#### `backend/services/transcription.py`
```python
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

def transcribe_audio_file(file_path: str) -> tuple[str, str]:
    """
    Transcribe audio using Whisper.
    
    Returns:
        (transcript_text, detected_language)
    """
    logger.info("Transcribing file: %s", file_path)
    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    transcript = result.text or ""
    detected_language = getattr(result, 'language', 'en')
    return transcript, detected_language
```

#### `backend/services/translation.py`
```python
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

def translate_text(text: str, target_language: str) -> str:
    """Translate text to target language using GPT-4o-mini"""
    if not text:
        return ""
    
    prompt = f"""Translate the following text to {target_language}. 
Only provide the translated text, nothing else.

Text:
{text}"""
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    return response.choices[0].message.content.strip()

def detect_and_translate_if_needed(transcript: str, source_language: str) -> tuple[str, str, bool]:
    """
    Detect language and translate to English if needed.
    
    Returns:
        (translated_transcript, detected_language, was_translated)
    """
    # [Copy existing logic from app.py]
```

#### `backend/services/summarization.py`
```python
import logging
import json
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

def summarize_and_extract_actions(transcript: str, agenda: str = "", detected_language: str = "English"):
    """
    Summarize transcript and extract action items.
    
    Returns:
        (summary, action_items, memo_json)
    """
    # [Copy existing logic from app.py]
```

#### `backend/services/qa_detection.py`
```python
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)
client = OpenAI()

def auto_detect_qa(transcript: str) -> list:
    """Auto-detect questions and answers in transcript"""
    # [Copy existing auto_detect_qa function from app.py]
```

#### `backend/services/export.py`
```python
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

def generate_pdf(data: dict) -> bytes:
    """Generate PDF from meeting data"""
    # [Copy existing generate_pdf logic from app.py]

def export_to_json(data: dict) -> str:
    """Export meeting data to JSON"""
    import json
    return json.dumps(data, indent=2, ensure_ascii=False)

def export_to_text(data: dict) -> str:
    """Export meeting data to plain text"""
    lines = [
        f"Meeting: {data.get('title', 'Untitled')}",
        f"Date: {data.get('date', 'N/A')}",
        f"Language: {data.get('original_language', 'Unknown')}",
        "",
        "SUMMARY",
        "=" * 40,
        data.get('summary', ''),
        "",
        "ACTION ITEMS",
        "=" * 40,
    ]
    
    for item in data.get('action_items', []):
        lines.append(f"- {item}")
    
    lines.extend(["", "TRANSCRIPT", "=" * 40])
    lines.append(data.get('transcript', ''))
    
    return '\n'.join(lines)
```

**Deliverable**: 5 new service modules with extracted functions

---

### STEP 5: Create API Routes (Day 3-4 - 4 hours)

**Action**: Create new API route handlers

#### `backend/routes/api.py`
```python
from flask import Blueprint, request, jsonify
from backend.services import transcription, translation, summarization

api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

@api_bp.route('/process', methods=['POST'])
def process_meeting():
    """Process audio file (keep existing logic)"""
    # Move existing /process logic here
    pass

@api_bp.route('/translate_content', methods=['POST'])
def translate_content():
    """Translate summary and transcript"""
    # Move existing /translate_content logic here
    pass

@api_bp.route('/detect_questions', methods=['POST'])
def detect_questions():
    """Auto-detect questions"""
    # Move existing /detect_questions logic here
    pass
```

#### `backend/routes/settings.py`
```python
from flask import Blueprint, request, jsonify
from backend.models import db, Setting

settings_bp = Blueprint('settings', __name__, url_prefix='/api/v1/settings')

@settings_bp.route('', methods=['GET'])
def get_settings():
    """Get all admin settings"""
    settings = Setting.query.all()
    return jsonify({s.key: s.value for s in settings})

@settings_bp.route('', methods=['POST'])
def update_settings():
    """Update admin settings"""
    data = request.json
    for key, value in data.items():
        Setting.set(key, value)
    return jsonify({'status': 'success'})
```

#### `backend/routes/history.py`
```python
from flask import Blueprint, request, jsonify
from backend.models import db, Meeting

history_bp = Blueprint('history', __name__, url_prefix='/api/v1/history')

@history_bp.route('/meetings', methods=['GET'])
def list_meetings():
    """List all meetings"""
    meetings = Meeting.query.order_by(Meeting.created_at.desc()).all()
    return jsonify([m.to_dict() for m in meetings])

@history_bp.route('/meetings/<meeting_id>', methods=['GET'])
def get_meeting(meeting_id):
    """Get specific meeting"""
    meeting = Meeting.query.get(meeting_id)
    if not meeting:
        return jsonify({'error': 'Meeting not found'}), 404
    return jsonify(meeting.to_dict())
```

**Deliverable**: Clean API routes organized by concern

---

### STEP 6: Update Flask App to Use New Modules (Day 4 - 2 hours)

**Action**: Modify `app.py` to import and use new modules

**Key changes to app.py**:
```python
# At the top, add:
from backend.models import db, Meeting, Setting
from backend.routes.api import api_bp
from backend.routes.settings import settings_bp
from backend.routes.history import history_bp

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(history_bp)

# Keep existing /process endpoint but have it call the service:
# from backend.services.transcription import transcribe_audio_file
# from backend.services.summarization import summarize_and_extract_actions
# etc.

# Create database tables
with app.app_context():
    db.create_all()
```

**Deliverable**: `app.py` refactored to use new modules (incrementally)

---

### STEP 7: Add Database Migration (Day 4 - 1 hour)

**Action**: Set up Alembic for database migrations

```bash
pip install alembic
alembic init migrations
```

Create initial migration:
```bash
alembic revision --autogenerate -m "Initial schema: meetings, settings, export_history"
alembic upgrade head
```

**Deliverable**: Database tables created in SQLite

---

### STEP 8: Update requirements.txt (Day 4 - 30 min)

**Add to requirements.txt**:
```
flask-sqlalchemy==3.1.1
alembic==1.13.0
flask-cors==4.0.0  # For future mobile apps
python-dotenv==1.0.0  # For environment variables
```

**Run**:
```bash
pip install -r requirements.txt
```

**Deliverable**: New dependencies installed

---

### STEP 9: Test Backend Refactoring (Day 5 - 2 hours)

**Action**: Create simple tests to verify services work

**Create**: `tests/test_services.py`
```python
import pytest
from backend.services.translation import translate_text

def test_translate_text():
    """Test translation works"""
    result = translate_text("Hello", "Spanish")
    assert result.lower() in ["hola", "hola!"]

# Add more tests...
```

**Run tests**:
```bash
pip install pytest
pytest tests/
```

**Deliverable**: Tests passing, services working

---

## 📊 Summary of Phase 1 Progress

After completing these steps (5-6 days):

### ✅ Done
- New folder structure
- Database models created
- Services extracted from app.py
- New API routes organized
- Database migrations set up
- Old functionality preserved
- Tests passing

### Structure Achieved
```
backend/
├── services/          # Clean, testable service layer
│   ├── transcription.py
│   ├── translation.py
│   ├── summarization.py
│   ├── qa_detection.py
│   └── export.py
├── routes/            # API endpoints organized
│   ├── api.py
│   ├── settings.py
│   └── history.py
└── models.py          # Database layer

Database:
├── meetings           # Stores meeting data
├── settings           # Stores configuration
└── export_history     # Tracks exports
```

### 🚀 Ready for Next Phase
- Phase 2: Frontend refactoring
- Phase 3: Add new features (admin UI, email export)
- Phase 4: Mobile app support

---

## 🎯 Success Checklist for Phase 1

- [ ] Answer the 6 decision questions
- [ ] Create folder structure
- [ ] Create database models
- [ ] Extract services from app.py
- [ ] Create API route handlers
- [ ] Update Flask app to use blueprints
- [ ] Set up database migrations
- [ ] Update requirements.txt
- [ ] Tests passing
- [ ] Existing features still work
- [ ] Commit all changes to GitHub

---

## ⚠️ Important Notes

**DO NOT**:
- Delete any existing code yet
- Break existing functionality
- Change HTML/CSS
- Remove current endpoints

**DO**:
- Keep old code as fallback during transition
- Test frequently
- Commit incremental changes
- Document as you go
- Keep existing app.py working while building new structure

**Timeline**: This Phase 1 should take 5-7 days of focused work

---

## Next After Phase 1?

Once Phase 1 is complete, you'll have:
1. ✅ Clean, modular backend
2. ✅ Database for persistence
3. ✅ Well-organized API
4. ✅ Ready for feature additions

**Then move to Phase 2**: Frontend refactoring and modularization

---

**Questions?** Start here with STEP 1 (answer decisions) → STEP 2 (create structure) → STEP 3 (database) ...

**Ready to begin?** Start with the decision checklist above!
