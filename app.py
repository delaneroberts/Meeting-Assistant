import os
import time
import json
import logging
import subprocess
import re
from datetime import datetime
from io import BytesIO

from flask import Flask, render_template, request, jsonify, send_file, abort, url_for
from werkzeug.utils import secure_filename

from openai import OpenAI

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


# ----------------------------
# Config / Folders
# ----------------------------
UPLOAD_FOLDER = "uploads"
TRANSCRIPT_FOLDER = "transcripts"
LOG_FOLDER = "logs"

MAX_FILE_AGE_SECONDS = 60 * 60  # 1 hour
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# ----------------------------
# Logging
# ----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_FOLDER, "app.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ----------------------------
# Flask + OpenAI client
# ----------------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

client = OpenAI()  # reads OPENAI_API_KEY from environment


# ----------------------------
# Housekeeping
# ----------------------------
def cleanup_old_files() -> None:
    """Delete old audio + transcript files."""
    now = time.time()
    for folder in (UPLOAD_FOLDER, TRANSCRIPT_FOLDER):
        if not os.path.isdir(folder):
            continue
        for name in os.listdir(folder):
            path = os.path.join(folder, name)
            try:
                if os.path.isfile(path):
                    age = now - os.path.getmtime(path)
                    if age > MAX_FILE_AGE_SECONDS:
                        os.remove(path)
                        logger.info("Deleted old file: %s", path)
            except Exception as e:
                logger.warning("Cleanup error on %s: %s", path, e)


# ----------------------------
# Transcription
# ----------------------------
def transcribe_audio_file(file_path: str) -> tuple[str, str]:
    """
    Use OpenAI Whisper to transcribe audio to text.
    
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
    # Whisper automatically detects language; we'll use GPT to confirm
    detected_language = getattr(result, 'language', 'en')
    return transcript, detected_language


# ----------------------------
# Language Detection & Translation
# ----------------------------
def detect_and_translate_if_needed(text: str, source_language: str = "") -> tuple[str, str, bool]:
    """
    Detect the language of the text and translate to English if needed.
    
    Returns:
        (translated_text, language_name, was_translated)
    """
    if not text.strip():
        return text, "Unknown", False
    
    # Use GPT to detect language
    detection_prompt = f"""Analyze this text and respond with ONLY a JSON object (no other text):

{{
  "detected_language": "Language name (e.g., 'English', 'Spanish', 'French', 'Cantonese', 'Mandarin Chinese', etc.)",
  "language_code": "ISO 639-1 code (e.g., 'en', 'es', 'fr', 'yue', 'zh', etc.)",
  "is_english": true or false
}}

Text to analyze:
\"\"\"{text[:1000]}\"\"\"
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": detection_prompt}
            ],
            temperature=0.0,
            max_tokens=200,
        )
        
        response_text = (response.choices[0].message.content or "").strip()
        result = json.loads(response_text)
        
        language_name = result.get("detected_language", "Unknown")
        is_english = result.get("is_english", True)
        
        logger.info("Detected language: %s (is_english: %s)", language_name, is_english)
        
        # If already English, return as-is
        if is_english:
            return text, language_name, False
        
        # For non-English, translate to English
        logger.info("Translating %s text (%d chars) to English", language_name, len(text))
        
        try:
            translation_prompt = f"""Translate the following {language_name} text to English. 
Provide ONLY the English translation, word-for-word and complete, with no explanations or comments.

{language_name} text:
\"\"\"{text}\"\"\"

English translation:"""
            
            translation_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "user", "content": translation_prompt}
                ],
                temperature=0.0,
                max_tokens=4096,  # Increased to max allowed
            )
            
            translated_text = (translation_response.choices[0].message.content or "").strip()
            
            if translated_text:
                logger.info("Successfully translated %s text to English (%d chars -> %d chars)", language_name, len(text), len(translated_text))
                return translated_text, language_name, True
            else:
                logger.warning("Translation returned empty. Returning original text.")
                return text, language_name, False
                
        except Exception as e:
            logger.exception("Translation failed: %s. Returning original text in %s.", e, language_name)
            return text, language_name, False
        
    except Exception as e:
        logger.exception("Language detection failed: %s. Assuming original text is English.", e)
        return text, "Unknown", False


# ----------------------------
# Summarization (meeting-agnostic)
# ----------------------------
def _render_memo_to_text(data: dict) -> str:
    """
    Convert structured memo JSON into a readable, well-spaced summary
    suitable for on-screen reading and PDFs.
    """
    title = (data.get("title") or "Meeting Notes").strip()
    mtype = (data.get("meeting_type") or "other").strip()

    lines: list[str] = []

    # Header
    lines.append(title)
    lines.append(f"Type: {mtype}")
    lines.append("")  # blank line

    def add_section(header: str, items: list[str]):
        if not items:
            return
        lines.append(header)
        lines.append("")  # space after header
        for it in items:
            s = str(it).strip()
            if s:
                lines.append(f"- {s}")
        lines.append("")  # space after section

    # Core sections
    add_section("Summary", data.get("summary_bullets") or [])
    add_section("Key Topics", data.get("key_topics") or [])
    add_section("Decisions", data.get("decisions") or [])
    add_section("Risks / Blockers", data.get("risks_blockers") or [])
    add_section("Open Questions", data.get("open_questions") or [])

    # Detailed notes
    sections = data.get("notes_by_section") or []
    if sections:
        lines.append("Details")
        lines.append("")
        for sec in sections:
            if not isinstance(sec, dict):
                continue
            heading = (sec.get("heading") or "").strip()
            bullets = sec.get("bullets") or []

            if heading:
                lines.append(heading)
                lines.append("")

            for b in bullets:
                s = str(b).strip()
                if s:
                    lines.append(f"- {s}")

            lines.append("")  # space between detail subsections

    # Trim trailing whitespace
    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def summarize_and_extract_actions(transcript: str, agenda: str = "", detected_language: str = "English"):
    """
    Returns:
      summary: str
      action_items: list[str]
      memo_json: dict

    Strategy:
    - Ask for JSON memo (meeting-type aware) to work for any meeting.
    - If agenda is provided, organize summary around agenda items.
    - Render memo into a readable summary string.
    - Normalize action items into list[str] for your UI.
    - Fallback to plain text if JSON mode fails.
    """
    logger.info("Summarizing transcript (%d chars), agenda present: %s, detected_language: %s", len(transcript or ""), bool(agenda.strip()), detected_language)

    agenda_instruction = ""
    if agenda.strip():
        agenda_instruction = f"""

IMPORTANT: The meeting had the following agenda:
{agenda}

When structuring your notes, organize them by agenda items. Any discussion that doesn't fit the agenda should be placed in sections labeled "Opening Conversation" or "Other".
In the notes_by_section, use the agenda items as headings where applicable."""

    prompt_text = f"""
You are an enterprise meeting assistant.

Step 1: Identify meeting type.
Choose ONE meeting_type from:
recruiting, interview, sales, customer_discovery, planning, status_update, standup, technical_review, support, 1on1, other

Step 2: Produce a structured meeting memo as JSON using EXACTLY this schema:

{{
  "meeting_type": "...",
  "title": "Short descriptive title (max 10 words)",
  "summary_bullets": ["3-8 bullets, high signal"],
  "key_topics": ["3-10 short topic phrases"],
  "decisions": [],
  "action_items": [
    {{"item":"Action", "owner":"Name/role or Unassigned", "due":"Date or Not stated"}}
  ],
  "risks_blockers": [],
  "open_questions": [],
  "notes_by_section": [
    {{"heading":"Section heading", "bullets":["Bullets..."]}}
  ]
}}

Rules:
- Use ONLY what is explicitly stated in the transcript. Do NOT infer.
- Preserve exact numbers and commitments verbatim (prices, dates, headcount, utilization, SLA, etc.).
- If something is not discussed, leave arrays empty ([]) rather than adding filler.
- Keep it concise and actionable.
- Action items should only include explicit commitments or clearly assigned next steps.{agenda_instruction}

Transcript:
\"\"\"{transcript}\"\"\"
""".strip()

    # --- Attempt structured JSON output (newer SDKs) ---
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are precise and structured."},
                {"role": "user", "content": prompt_text},
            ],
            temperature=0.2,
            max_tokens=900,
            # Some SDK versions don't support this; we catch and fallback below.
            response_format={"type": "json_object"},
        )

        content = (resp.choices[0].message.content or "").strip()
        data = json.loads(content) if content else {}

        summary_text = _render_memo_to_text(data)

        # Normalize action items to list[str] for existing UI
        action_items_raw = data.get("action_items") or []
        action_items: list[str] = []
        for ai in action_items_raw:
            if isinstance(ai, str):
                s = ai.strip()
                if s:
                    action_items.append(s)
            elif isinstance(ai, dict):
                item = (ai.get("item") or "").strip()
                owner = (ai.get("owner") or "Unassigned").strip()
                due = (ai.get("due") or "Not stated").strip()
                if item:
                    action_items.append(f"{item} — {owner} (Due: {due})")

        return summary_text, action_items, data

    except Exception as e:
        logger.exception("Structured summarization failed; using fallback. Error: %s", e)

    # --- Fallback: plain text (always works) ---
    fallback_prompt = f"""
Summarize the transcript in 5-10 bullet points (high signal, no fluff).
Then list action items as '-' bullets in the format: "Action — Owner (Due: ...)".
If none, write: None.

Transcript:
\"\"\"{transcript}\"\"\"
""".strip()

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": fallback_prompt}],
            temperature=0.2,
            max_tokens=900,
        )
        text = (resp.choices[0].message.content or "").strip()
        action_items = [ln[2:].strip() for ln in text.splitlines() if ln.strip().startswith("- ")]
        return text, action_items, {}
    except Exception as e2:
        logger.exception("Fallback summarization failed: %s", e2)
        return "", [], {}


# ----------------------------
# Meeting artifact storage (JSON)
# ----------------------------
_MEETING_ID_RE = re.compile(r"^[A-Za-z0-9_-]{6,80}$")


def new_meeting_id() -> str:
    # 20260109_104455_123
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]


def safe_meeting_id(meeting_id: str) -> str:
    if not meeting_id or not _MEETING_ID_RE.match(meeting_id):
        raise ValueError("Invalid meeting_id")
    return meeting_id


def meeting_json_path(meeting_id: str) -> str:
    meeting_id = safe_meeting_id(meeting_id)
    return os.path.join(TRANSCRIPT_FOLDER, f"{meeting_id}.json")


def save_meeting_artifacts(meeting_id: str, filename: str, transcript: str, summary: str, action_items: list, original_language: str = "English", was_translated: bool = False) -> None:
    payload = {
        "meeting_id": meeting_id,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source_filename": filename,
        "original_language": original_language,
        "was_translated": was_translated,
        "transcript": transcript or "",
        "summary": summary or "",
        "action_items": action_items or [],
    }
    with open(meeting_json_path(meeting_id), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_meeting_artifacts(meeting_id: str) -> dict:
    path = meeting_json_path(meeting_id)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def delete_meeting_artifacts(meeting_id: str) -> None:
    path = meeting_json_path(meeting_id)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


# ----------------------------
# PDF generation
# ----------------------------
def build_pdf_bytes(data: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
    )
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Meeting Assistant Report", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"Meeting ID: {data.get('meeting_id','')}", styles["Normal"]))
    story.append(Paragraph(f"Created: {data.get('created_at','')}", styles["Normal"]))
    src = data.get("source_filename") or ""
    if src:
        story.append(Paragraph(f"Source file: {src}", styles["Normal"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Summary", styles["Heading2"]))
    story.append(Paragraph((data.get("summary") or "").replace("\n", "<br/>"), styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Action Items", styles["Heading2"]))
    items = data.get("action_items") or []
    if items:
        story.append(
            ListFlowable(
                [ListItem(Paragraph(str(x), styles["BodyText"])) for x in items],
                bulletType="1",
            )
        )
    else:
        story.append(Paragraph("No action items found.", styles["BodyText"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Transcript", styles["Heading2"]))
    story.append(Paragraph((data.get("transcript") or "").replace("\n", "<br/>"), styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()


# ----------------------------
# Routes
# ----------------------------
@app.errorhandler(413)
def file_too_large(e):
    return jsonify({"error": "File is too large. Limit is 25 MB."}), 413


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process():
    cleanup_old_files()

    if "audio_file" not in request.files:
        return jsonify({"error": "No file part in request."}), 400

    file = request.files["audio_file"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    logger.info("Saved file to: %s", os.path.abspath(save_path))

    # Get agenda from request if present
    agenda = request.form.get("agenda", "").strip()

    # Transcribe
    try:
        transcript_text, source_language = transcribe_audio_file(save_path)
    except Exception as e:
        logger.exception("Error processing the audio file")
        return jsonify({"error": f"Error processing the audio file: {e}"}), 500

    # Store the original (untranslated) transcript
    original_transcript = transcript_text

    # Detect language and translate if needed
    translated_transcript, detected_language, was_translated = detect_and_translate_if_needed(transcript_text, source_language)
    
    if was_translated:
        logger.info("Transcript translated from %s to English", detected_language)

    # Save original transcript as .txt
    base, _ = os.path.splitext(filename)
    transcript_filename = f"{base}.txt"
    transcript_path = os.path.join(TRANSCRIPT_FOLDER, transcript_filename)
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            # Save the translated version in the transcript file
            f.write(translated_transcript)
        logger.info("Saved transcript to: %s", os.path.abspath(transcript_path))
    except Exception:
        logger.exception("Error saving transcript")
        transcript_filename = ""

    # Summarize (with agenda if provided, using English/translated transcript for better accuracy)
    try:
        summary, action_items, memo_json = summarize_and_extract_actions(translated_transcript, agenda, detected_language)
    except Exception:
        logger.exception("Error summarizing transcript")
        summary, action_items = "", []

    # Generate original language version if not English
    original_summary = summary
    original_action_items = action_items
    if was_translated and detected_language and detected_language.lower() != "english":
        try:
            translate_prompt = f"""Translate this meeting summary to {detected_language}. Keep the structure and meaning intact. Only provide the translated text.

Summary:
{summary}"""
            translate_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": translate_prompt}],
                max_tokens=2048,
            )
            original_summary = translate_response.choices[0].message.content.strip()
            logger.info("Translated summary to %s", detected_language)
        except Exception as e:
            logger.warning("Could not translate summary to %s: %s", detected_language, e)
            original_summary = summary  # Fallback to English
        
        # Translate action items
        try:
            action_items_text = "\n".join(action_items)
            action_items_prompt = f"""Translate these action items to {detected_language}. Keep the structure and meaning intact. Return as a numbered list.

Action Items:
{action_items_text}"""
            action_items_response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": action_items_prompt}],
                max_tokens=1024,
            )
            translated_items_text = action_items_response.choices[0].message.content.strip()
            # Parse the translated items back into a list
            original_action_items = [item.strip() for item in translated_items_text.split('\n') if item.strip()]
            logger.info("Translated action items to %s", detected_language)
        except Exception as e:
            logger.warning("Could not translate action items to %s: %s", detected_language, e)
            original_action_items = action_items  # Fallback to English

    # Save canonical meeting artifact JSON
    meeting_id = new_meeting_id()
    # Save the raw memo JSON (for debugging / inspection)
    try:
        memo_path = os.path.join(TRANSCRIPT_FOLDER, f"{meeting_id}_memo.json")
        with open(memo_path, "w", encoding="utf-8") as f:
            json.dump(memo_json, f, ensure_ascii=False, indent=2)
        logger.info("Saved memo JSON to: %s", os.path.abspath(memo_path))
    except Exception:
        logger.exception("Error saving memo JSON")
    try:
        save_meeting_artifacts(
            meeting_id=meeting_id,
            filename=filename,
            transcript=translated_transcript,
            summary=summary,
            action_items=action_items,
            original_language=detected_language,
            was_translated=was_translated,
        )
        logger.info("Saved meeting artifacts JSON: %s", os.path.abspath(meeting_json_path(meeting_id)))
    except Exception:
        logger.exception("Error saving meeting artifacts JSON")

    # Optionally delete the audio file after processing
    try:
        os.remove(save_path)
        logger.info("Deleted audio file: %s", save_path)
    except Exception as e:
        logger.warning("Could not delete audio file %s: %s", save_path, e)

    return jsonify(
        {
            "meeting_id": meeting_id,
            "transcript": original_transcript,
            "english_transcript": translated_transcript,
            "summary": original_summary,
            "english_summary": summary,
            "action_items": original_action_items,
            "english_action_items": action_items,
            "transcript_file": transcript_filename,
            "original_language": detected_language,
            "was_translated": was_translated,
            "download_url": url_for("download_pdf", meeting_id=meeting_id),
            "discard_url": url_for("discard_meeting", meeting_id=meeting_id),
            "memo_json": memo_json,
        }
    )


@app.route("/download/<meeting_id>", methods=["GET"])
def download_pdf(meeting_id):
    try:
        data = load_meeting_artifacts(meeting_id)
    except (ValueError, FileNotFoundError):
        abort(404)

    pdf_bytes = build_pdf_bytes(data)
    filename = f"{meeting_id}_meeting_report.pdf"

    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/discard/<meeting_id>", methods=["POST"])
def discard_meeting(meeting_id):
    try:
        safe_meeting_id(meeting_id)
        delete_meeting_artifacts(meeting_id)
    except ValueError:
        abort(400)
    return jsonify({"status": "discarded", "meeting_id": meeting_id})


@app.route("/open_transcripts", methods=["POST"])
def open_transcripts():
    """On macOS, open the transcripts folder in Finder."""
    folder = os.path.abspath(TRANSCRIPT_FOLDER)
    try:
        subprocess.run(["open", folder], check=True)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.warning("Could not open transcripts folder: %s", e)
        return jsonify({"error": "Could not open transcripts folder."}), 500


@app.route("/detect_questions", methods=["POST"])
def detect_questions():
    """
    Detect questions in new transcript and answer them automatically.
    """
    try:
        data = request.get_json()
        new_transcript = (data.get("new_transcript") or "").strip()
        full_transcript = (data.get("full_transcript") or "").strip()

        if not new_transcript or len(new_transcript) < 20:
            return jsonify({"questions": []})

        logger.info("Detecting questions in %d char transcript snippet", len(new_transcript))

        # Use GPT to detect questions and determine if rhetorical
        detection_prompt = f"""Analyze this transcript snippet and identify any questions asked.

For each question found:
1. Extract the exact question (verbatim from the transcript)
2. Determine if it's a rhetorical question (asked for effect, not expecting answer) or a real question
3. If it's a real question, answer it based on the FULL meeting transcript so far

Respond with ONLY a JSON array (no other text):
[
  {{
    "question": "What was the deadline mentioned?",
    "is_rhetorical": false,
    "answer": "The deadline is March 15, 2026."
  }},
  {{
    "question": "Isn't that amazing?",
    "is_rhetorical": true,
    "answer": "This is marked as rhetorical and doesn't need an answer."
  }}
]

If no questions are found, return an empty array: []

New transcript snippet:
\"\"\"{new_transcript}\"\"\"

Full transcript context:
\"\"\"{full_transcript}\"\"\"
"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": detection_prompt}
            ],
            temperature=0.5,
            max_tokens=1000,
        )

        response_text = (response.choices[0].message.content or "").strip()
        
        try:
            questions = json.loads(response_text)
            if not isinstance(questions, list):
                questions = []
        except json.JSONDecodeError:
            logger.warning("Failed to parse question detection response: %s", response_text)
            questions = []

        logger.info("Detected %d questions", len(questions))

        return jsonify({
            "questions": questions
        })

    except Exception as e:
        logger.exception("Question detection error: %s", e)
        return jsonify({"questions": [], "error": str(e)}), 500


@app.route("/translate_content", methods=["POST"])
def translate_content():
    """Endpoint to translate summary and transcript to target language"""
    data = request.json
    summary = data.get("summary", "")
    transcript = data.get("transcript", "")
    target_language = data.get("target_language", "English")
    
    if not summary or not transcript:
        return jsonify({"error": "Summary and transcript are required"}), 400
    
    try:
        # Translate summary
        summary_prompt = f"""Translate the following meeting summary to {target_language}. Keep the same structure and meaning. Only provide the translated text, nothing else.

Summary:
{summary}"""
        
        summary_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": summary_prompt}],
            max_tokens=2048,
        )
        translated_summary = summary_response.choices[0].message.content.strip()
        
        # Translate transcript
        transcript_prompt = f"""Translate the following meeting transcript to {target_language}. Maintain the speaker labels and structure. Only provide the translated text, nothing else.

Transcript:
{transcript}"""
        
        transcript_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": transcript_prompt}],
            max_tokens=4096,
        )
        translated_transcript = transcript_response.choices[0].message.content.strip()
        
        return jsonify({
            "translated_summary": translated_summary,
            "translated_transcript": translated_transcript,
        })
    
    except Exception as e:
        logger.exception("Translation error: %s", e)
        return jsonify({"error": str(e)}), 500


# ----------------------------
# Main
# ----------------------------
if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("WARNING: OPENAI_API_KEY is not set in the environment.")
    # Allow connections from local network (iPhone/iPad on same WiFi)
    app.run(host="0.0.0.0", port=8000, debug=True)
