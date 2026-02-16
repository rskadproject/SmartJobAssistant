import os
import json
import requests
import logging # Added logging
import tempfile # For safe temp dirs
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import PyPDF2
import docx
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
# Import helpers
from ai_helpers import extract_text_from_pdf, extract_text_from_docx, analyze_with_ai, generate_summary_ai

# Setup Logging (Visible in Render Logs)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Google Gemini
# import google.generativeai as genai

# Configure Google Gemini
api_key = os.getenv("GEMINI_API_KEY")

# Supabase Setup
# Supabase Setup
from supabase import create_client, Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    print("CRITICAL ERROR: SUPABASE_URL is missing from environment", flush=True)
if not SUPABASE_KEY:
    print("CRITICAL ERROR: SUPABASE_KEY is missing from environment", flush=True)

try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("Supabase client initialized successfully", flush=True)
except Exception as e:
    print(f"CRITICAL ERROR: Failed to init Supabase: {e}", flush=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev_warning_change_me_in_prod')

# Use system temp directory for uploads
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir() 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

ALLOWED_EXTENSIONS = {'pdf', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/config')
def get_config():
    return jsonify({
        "supabase_url": SUPABASE_URL,
        "supabase_key": SUPABASE_KEY
    })







@app.route('/analyze', methods=['POST'])
def analyze():
    if 'resume' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['resume']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
        
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Extract Text
        text = ""
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(filepath)
            
        if not text.strip():
            return jsonify({"error": "Could not extract text from file."}), 400
            
        # Analyze
        analysis = analyze_with_ai(text)

        # Log to Supabase (Analytics Only - No PII)
        try:
            # We don't store the file or text, just that a scan happened
            supabase.table('scan_logs').insert({
                "status": "Success",
                "ats_score": analysis.get('ats_score', 0)
            }).execute()
        except Exception as e:
            logging.error(f"Supabase Log Error: {e}")
        
        # Cleanup
        try:
            os.remove(filepath)
        except:
            pass
            
        return jsonify(analysis)
    
    return jsonify({"error": "Invalid file type"}), 400









if __name__ == '__main__':
    app.run(debug=True)
