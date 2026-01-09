import os
import time
import json
import logging
import subprocess

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI

# Folders
UPLOAD_FOLDER = "uploads"
TRANSCRIPT_FOLDER = "transcripts"
LOG_FOLDER = "logs"

MAX_FILE_AGE_SECONDS = 60 * 60  # 1 hour
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB limit

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSCRIPT_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_FOLDER, "app.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH

client = OpenAI()  # uses OPENAI_API_KEY from your environment


def cleanup_old_files():
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


def transcribe_audio_file(file_path: str) -> str:
    """Use OpenAI Whisper API to transcribe audio to text."""
    logger.info("Transcribing file: %s", file_path)
    with open(file_path, "rb") as f:
        result = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return result.text


def summarize_and_extract_actions(transcript: str):
    """
    Use a chat model to generate:
    - summary (string)
    - action_items (list of strings)
    """
    logger.info("Summarizing transcript (%d chars)", len(transcript))

    prompt = {
        "role": "user",
        "content": f"""
You are a helpful meeting assistant.

Given the meeting transcript below, produce:
1) A concise summary (3–6 sentences).
2) A list of concrete action items.

Return your answer strictly as JSON with this shape:
{{
  "summary": "short paragraph here",
  "action_items": ["item 1", "item 2", "..."]
}}

Transcript:
\"\"\"{transcript}\"\"\"
"""
    }

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a precise and structured meeting assistant."},
            prompt,
        ],
        temperature=0.3,
        max_tokens=800,
        response_format={"type": "json_object"},
    )

    data = json.loads(response.choices[0].message.content)
    summary = data.get("summary", "").strip()
    action_items = data.get("action_items", [])
    return summary, action_items


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

    # Save audio file
    filename = secure_filename(file.filename)
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    file.save(save_path)
    logger.info("Saved file to: %s", os.path.abspath(save_path))

    # Transcribe
    try:
        transcript_text = transcribe_audio_file(save_path)
    except Exception as e:
        logger.exception("Error processing the audio file")
        # Friendlier error to UI
        return jsonify({"error": f"Error processing the audio file: {e}"}), 500

    # Save transcript
    base, _ = os.path.splitext(filename)
    transcript_filename = f"{base}.txt"
    transcript_path = os.path.join(TRANSCRIPT_FOLDER, transcript_filename)
    try:
        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript_text)
        logger.info("Saved transcript to: %s", os.path.abspath(transcript_path))
    except Exception as e:
        logger.exception("Error saving transcript")
        # not fatal to the user, they still see the text
        transcript_filename = ""

    # Summarize + extract actions
    try:
        summary, action_items = summarize_and_extract_actions(transcript_text)
    except Exception as e:
        logger.exception("Error summarizing transcript")
        summary = ""
        action_items = []

    # Optionally delete the audio file after processing
    try:
        os.remove(save_path)
        logger.info("Deleted audio file: %s", save_path)
    except Exception as e:
        logger.warning("Could not delete audio file %s: %s", save_path, e)

    return jsonify(
        {
            "transcript": transcript_text,
            "summary": summary,
            "action_items": action_items,
            "transcript_file": transcript_filename,
        }
    )


@app.route("/open_transcripts", methods=["POST"])
def open_transcripts():
    """
    On macOS, open the transcripts folder in Finder.
    """
    folder = os.path.abspath(TRANSCRIPT_FOLDER)
    try:
        subprocess.run(["open", folder], check=True)
        return jsonify({"status": "ok"})
    except Exception as e:
        logger.warning("Could not open transcripts folder: %s", e)
        return jsonify({"error": "Could not open transcripts folder."}), 500


if __name__ == "__main__":
    if not os.environ.get("OPENAI_API_KEY"):
        logger.warning("WARNING: OPENAI_API_KEY is not set in the environment.")
    app.run(host="0.0.0.0", port=8000, debug=True)
