# Meeting Assistant Refactoring Strategy
**Date**: February 11, 2026  
**Status**: Planning Phase (not yet implemented)

---

## Executive Summary

The Meeting Assistant has evolved from a basic MVP to a feature-rich application with multilingual support, translation, and mobile accessibility. Before adding major features (admin settings, email export, mobile apps), the codebase should be refactored to support these additions without accumulating technical debt.

**Recommendation**: Refactor existing code into modular components before adding new features.

---

## Current State

### ✅ Working Features
- Audio transcription via OpenAI Whisper
- Automatic language detection
- Meeting summarization with GPT-4o-mini
- Action item extraction
- Multilingual translation (13+ languages)
- Agenda support (upload or paste)
- Live recording from browser
- Auto-detect Q&A panel
- Copy buttons for summary and transcript
- Local network access (iPhone/iPad on same WiFi)
- PDF download of meeting notes

### 📁 Current Architecture
```
meeting_assistant/
├── app.py                 # Monolithic Flask backend (~812 lines)
├── static/script.js       # Monolithic frontend (~706 lines)
├── templates/index.html   # Single HTML page
├── uploads/              # Audio uploads
├── transcripts/          # Transcripts and JSONs
├── logs/                 # Application logs
└── requirements.txt      # Dependencies
```

### ⚠️ Current Limitations
- Single HTML page (not scalable for admin features)
- No user settings or configuration UI
- No email export functionality
- No file export (only PDF)
- No meeting history/search
- No database (only filesystem storage)
- Not suitable for mobile app wrapping
- Difficult to add new features without increasing complexity

---

## Proposed Features (Future Work)

### Feature 1: Admin Settings Screen
- Select transcription service (Whisper, Deepgram, AssemblyAI)
- Select LLM for summarization (GPT-4o-mini, Claude, Gemini)
- Configure API keys
- Set default language preferences
- Choose export formats

### Feature 2: Email Export
- Send summary and/or transcript via email
- Customizable email format (plain text, HTML, PDF attachment)
- Email history/log
- Bulk send to multiple recipients

### Feature 3: File Export
- Save to various formats (TXT, MD, JSON, PDF)
- Organize by date/meeting name
- Archive old meetings
- Search and retrieve past meetings

### Feature 4: Mobile Apps
- iOS app (via React Native or native Swift)
- Android app (via React Native or native Kotlin)
- Or: Progressive Web App (PWA) installable on iOS/Android

### Feature 5: Meeting History
- Database of past meetings
- Search by date, language, attendees
- Quick replay/re-summarize
- Export history

---

## Refactoring Strategy

### Phase 1: Backend Refactoring (2-3 weeks)

#### 1.1 Modularize app.py
Split into logical modules:

```
backend/
├── config.py              # Settings, constants, environment
├── services/
│   ├── __init__.py
│   ├── transcription.py   # Whisper API calls
│   ├── translation.py     # GPT translation logic
│   ├── summarization.py   # GPT summarization logic
│   ├── export.py          # Email, PDF, file export
│   └── qa_detection.py    # Q&A auto-detection
├── routes/
│   ├── __init__.py
│   ├── api.py            # /process, /translate_content endpoints
│   ├── settings.py       # /settings, /admin endpoints
│   └── export.py         # /export/email, /export/file endpoints
├── models.py             # Database models (SQLAlchemy)
├── database.py           # DB initialization and helpers
└── app.py               # Flask app setup (much cleaner)
```

**Benefits:**
- Each service is testable independently
- Easy to swap out services (e.g., use Claude instead of GPT)
- Settings endpoints separate from processing endpoints
- Clearer responsibility boundaries

#### 1.2 Add Database Layer
Use SQLite (local) with SQLAlchemy ORM:

```
meetings
├── id (primary key)
├── created_at
├── updated_at
├── audio_filename
├── original_language
├── transcript_original
├── transcript_english
├── summary_original
├── summary_english
├── action_items (JSON)
├── metadata (JSON) - agenda, attendees, etc.
└── export_history (relationship)

settings
├── id
├── user_id (for future multi-user)
├── transcription_service (whisper, deepgram, etc.)
├── llm_service (gpt-4o-mini, claude, gemini)
├── default_language
├── export_format (pdf, txt, json)
└── updated_at

export_history
├── id
├── meeting_id (foreign key)
├── export_type (email, file, pdf)
├── recipient (for email)
├── status (success, failed)
└── created_at
```

**Benefits:**
- Persistent storage beyond filesystem
- Search and filter meetings
- Track export history
- Foundation for future multi-user support

#### 1.3 Create API Structure
Clean, versioned REST API:

```
/api/v1/
├── /process              POST - Process audio (existing)
├── /translate_content    POST - Translate content (existing)
├── /detect_questions     POST - Auto-detect Q&A
├── /settings             GET/POST - Get/set admin settings
├── /meetings             GET - List past meetings
├── /meetings/{id}        GET - Get specific meeting
├── /export/email         POST - Send meeting via email
├── /export/file          POST - Export meeting to file
└── /export/pdf           GET - Generate PDF (existing, improved)
```

**Benefits:**
- Clear separation of concerns
- Easy to version API for future changes
- Mobile apps can use same API endpoints
- Cacheable responses

---

### Phase 2: Frontend Refactoring (1-2 weeks)

#### 2.1 Modularize script.js
Split into focused modules:

```
js/
├── api.js               # All fetch() calls to backend
├── audio.js             # Recording, upload, transcription
├── ui.js                # DOM manipulation, display logic
├── settings.js          # Admin settings UI and logic
├── export.js            # Email/file export UI
├── meeting-history.js   # Search, filter, display past meetings
├── utils.js             # Helper functions, constants
└── main.js              # Initialization
```

**Benefits:**
- Each module handles one concern
- Easier to test
- Reusable across pages
- Easier to add new features

#### 2.2 Add New Pages
Create separate HTML pages:

```
templates/
├── index.html           # Main processing page (keep mostly same)
├── admin.html           # Admin settings
├── history.html         # Meeting history/search
├── export.html          # Export options
└── layouts/
    └── base.html        # Shared layout/navbar
```

**Benefits:**
- Cleaner separation
- Can load different JS modules per page
- Easier to maintain
- Scales better with more features

#### 2.3 Improve UI/UX
- Add navigation bar (main, admin, history, export)
- Responsive design (already using Bootstrap)
- Loading states and progress indicators
- Better error messages
- Mobile-optimized layout

---

### Phase 3: Add New Features (2-3 weeks)

#### 3.1 Admin Settings Screen
- LLM selection dropdown with API key input
- Transcription service selection
- Default language preferences
- Save/load settings from database
- Test connection button

#### 3.2 Email Export
- Add email service (SendGrid, or simple SMTP)
- Email template builder (plain text, HTML)
- Single or bulk send
- Track delivery status

#### 3.3 File Export
- Export formats: TXT, MD, JSON, DOCX
- Save to local filesystem or cloud storage
- Naming conventions (date-based, custom)
- Batch export

#### 3.4 Meeting History
- Search by date range
- Filter by language, service used
- Quick actions (re-summarize, translate, export)
- Sort by date, language, size

---

### Phase 4: Mobile Apps (3-4 weeks)

#### Option A: React Native (Cross-platform)
- Single codebase for iOS and Android
- Reuse API endpoints from Phase 1
- Native look and feel
- Offline support possible
- **Timeline**: 3-4 weeks

#### Option B: PWA (Progressive Web App)
- Web app installable on iOS/Android home screen
- Works offline with service workers
- Smaller development effort
- **Timeline**: 2 weeks

#### Option C: Native (Longer but highest quality)
- iOS (Swift): 2-3 weeks
- Android (Kotlin): 2-3 weeks
- Separate development effort

**Recommendation for MVP**: Start with PWA (fastest), then graduate to React Native if needed.

---

## Implementation Roadmap

### Timeline
```
Week 1-3:   Phase 1 - Backend Refactoring
Week 4-5:   Phase 2 - Frontend Refactoring
Week 6-8:   Phase 3 - New Features
Week 9-12:  Phase 4 - Mobile Apps (or PWA)
```

**Total estimate**: 8-12 weeks of development

### Milestones
- **Week 3**: Backend modules complete, database working
- **Week 5**: Frontend modules complete, multi-page UI working
- **Week 8**: Admin settings, email export, file export functional
- **Week 12**: Mobile app (PWA or React Native) deployed

---

## Key Questions to Answer Before Starting

1. **LLM Selection**
   - Stick with GPT-4o-mini only, or support multiple?
   - Include local models (Ollama, LLaMA)?
   - Fallback strategy if API is down?

2. **Transcription Services**
   - Whisper only, or add Deepgram, AssemblyAI?
   - Cost considerations?
   - Language coverage?

3. **Email Capability**
   - Self-hosted SMTP or third-party (SendGrid)?
   - Authentication required?
   - Rate limits?

4. **Mobile Strategy**
   - PWA, React Native, or native?
   - Offline support required?
   - App store distribution (iOS/Android)?

5. **Database**
   - SQLite (local) or cloud (Firebase, PostgreSQL)?
   - Backup strategy?
   - Future cloud sync?

6. **User Management**
   - Single user (current) or multi-user?
   - Authentication/login?
   - Sharing capability?

---

## Risk Mitigation

### Risk 1: Refactoring breaks existing functionality
**Mitigation**: 
- Run existing features alongside new modules during transition
- Comprehensive test suite for each module
- Keep old code as fallback during transition period

### Risk 2: Technical debt during refactoring
**Mitigation**:
- Document code as you go
- Type hints in Python
- JSDoc comments in JavaScript
- Follow PEP-8 and ESLint standards

### Risk 3: Scope creep
**Mitigation**:
- Strict phase boundaries
- Deploy each phase before starting next
- Don't add features mid-refactor

### Risk 4: API design doesn't support future needs
**Mitigation**:
- Design API with versioning in mind (/api/v1/)
- Plan for multi-user from day one (even if not implementing)
- Review API design before implementation

---

## Success Criteria

### Phase 1 (Backend)
- ✅ All services are independent and testable
- ✅ Database stores meetings and settings
- ✅ API endpoints documented and working
- ✅ Existing functionality preserved

### Phase 2 (Frontend)
- ✅ Multi-page UI working
- ✅ Settings can be changed and persisted
- ✅ Meeting history searchable
- ✅ Mobile-responsive

### Phase 3 (Features)
- ✅ Email export working
- ✅ File export working
- ✅ Admin settings functional
- ✅ No performance degradation

### Phase 4 (Mobile)
- ✅ App installable on iOS/Android
- ✅ All core features accessible
- ✅ Offline support working

---

## Dependencies to Consider

### Backend
- Flask (existing)
- SQLAlchemy (new, for ORM)
- Alembic (new, for migrations)
- pytest (new, for testing)
- email-validator (new, for email export)
- python-docx (new, for DOCX export)

### Frontend
- Bootstrap (existing)
- No new frontend frameworks suggested (keep vanilla JS for now)

### Mobile (if React Native)
- React Native
- Expo or React Native CLI
- React Navigation
- Axios for API calls

---

## Testing Strategy

### Unit Tests (Python)
```
tests/
├── test_transcription.py
├── test_translation.py
├── test_summarization.py
├── test_export.py
└── test_models.py
```

### Integration Tests
- Test full workflow (upload → transcribe → summarize → export)
- Test database operations
- Test API endpoints

### Frontend Tests
- Jest for JavaScript unit tests
- Selenium for E2E tests
- Manual mobile testing

---

## Conclusion

This refactoring is a **strategic investment** that will:
1. Make the codebase maintainable long-term
2. Enable rapid feature development
3. Support mobile app integration
4. Reduce bugs and technical debt
5. Make collaboration easier

**Start with Phase 1** to establish solid foundation before adding new features.

---

## Quick Reference: What Changes When

| Aspect | Before | After |
|--------|--------|-------|
| **Files** | 3 main files | 15+ modules |
| **Storage** | Filesystem only | Database + filesystem |
| **Pages** | 1 HTML | 4-5 HTML pages |
| **API Endpoints** | 5 endpoints | 10+ endpoints |
| **Database** | None | SQLite with 3 tables |
| **Testability** | Low | High |
| **New Feature Time** | 1-2 weeks | 2-3 days |
| **Mobile Support** | None | Full support |

---

## Next Steps

1. **Answer the key questions above**
2. **Start new chat conversation** with this document
3. **Begin Phase 1: Backend Refactoring**
4. **Create detailed API specification** before coding
5. **Set up testing infrastructure** from day 1

---

**Document Version**: 1.0  
**Last Updated**: February 11, 2026  
**Status**: Ready for implementation planning
