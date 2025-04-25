import os
import sqlite3
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
import hashlib
import random
from datetime import datetime

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///puzzle_data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)

# Define database models
class DataEntry(db.Model):
    __tablename__ = 'data_entries'

    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(10), nullable=False)
    content_hash = db.Column(db.String(32), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # For backward compatibility
    @property
    def content(self):
        if self.category == 'idiom':
            return f"{self.question} - {self.answer}"
        return f"{self.question} {self.answer}"

    def __repr__(self):
        return f'<DataEntry {self.id}: {self.category}>'

    @staticmethod
    def generate_hash(question, answer):
        """Generate MD5 hash for question and answer to ensure uniqueness"""
        combined = f"{question}|{answer}"
        return hashlib.md5(combined.encode()).hexdigest()

# Ensure data directory exists and database file is created
db_uri = app.config['SQLALCHEMY_DATABASE_URI']
if db_uri.startswith('sqlite:///'):
    db_path = db_uri.replace('sqlite:///', '')
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.getcwd(), db_path)

    # Create directory if it doesn't exist
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"Created directory: {db_dir}")

    # Remove empty database file if it exists but has zero size
    if os.path.exists(db_path) and os.path.getsize(db_path) == 0:
        try:
            os.remove(db_path)
            print(f"Removed empty database file: {db_path}")
        except Exception as e:
            print(f"Error removing empty database file: {e}")

    # Create a new database file using direct SQLite connection if it doesn't exist
    if not os.path.exists(db_path):
        try:
            # Create an empty SQLite database file
            conn = sqlite3.connect(db_path)
            conn.close()
            print(f"Created new SQLite database file: {db_path}")
        except Exception as e:
            print(f"Error creating SQLite database file: {e}")

# Initialize database within app context
with app.app_context():
    try:
        # Create all tables
        db.create_all()
        print("Database tables created successfully")
    except Exception as e:
        print(f"Error creating database tables: {e}")

# Context processor to make datetime available in all templates
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# Routes
@app.route('/')
def index():
    return render_template('index.html')

# API Routes
@app.route('/api/random/<int:count>', methods=['GET'])
def get_random_entries(count):
    category = request.args.get('category')

    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)

    # Get total count of matching entries
    total_entries = query.count()

    # If requested count is more than available, return all available
    if count > total_entries:
        count = total_entries

    # Get random entries
    if total_entries > 0:
        # SQLite-specific random ordering
        random_entries = query.order_by(db.func.random()).limit(count).all()

        result = [{
            'id': entry.id,
            'question': entry.question,
            'answer': entry.answer,
            'category': entry.category,
            'created_at': entry.created_at.isoformat()
        } for entry in random_entries]

        return jsonify(result)
    else:
        return jsonify([])

@app.route('/api/add', methods=['POST'])
def add_entry():
    data = request.get_json()

    # Check for new format (question/answer)
    if data and 'question' in data and 'answer' in data and 'category' in data:
        question = data['question'].strip()
        answer = data['answer'].strip()
        category = data['category'].lower()

        # Validate fields
        if not question or not answer:
            return jsonify({'error': 'Question and answer cannot be empty'}), 400
    # Check for old format (content)
    elif data and 'content' in data and 'category' in data:
        content = data['content'].strip()
        category = data['category'].lower()

        # Validate content
        if not content:
            return jsonify({'error': 'Content cannot be empty'}), 400

        # Split content into question and answer based on category
        if category == 'riddle' or category == 'joke':
            # For riddles and jokes, try to split at the question mark
            parts = content.split('?', 1)
            if len(parts) > 1:
                question = parts[0].strip() + '?'
                answer = parts[1].strip()
            else:
                # If no question mark, use the whole content as question
                question = content
                answer = "No answer provided"
        elif category == 'idiom':
            # For idioms, split at the dash
            parts = content.split('-', 1)
            if len(parts) > 1:
                question = parts[0].strip()
                answer = parts[1].strip()
            else:
                # If no dash, use the whole content as question
                question = content
                answer = "No meaning provided"
        else:
            question = content
            answer = ""
    else:
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate category
    if category not in ['riddle', 'joke', 'idiom']:
        return jsonify({'error': 'Invalid category. Must be one of: riddle, joke, idiom'}), 400

    # Generate hash for deduplication
    content_hash = DataEntry.generate_hash(question, answer)

    # Check if entry already exists
    existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
    if existing_entry:
        return jsonify({'error': 'This entry already exists in the database'}), 409

    # Create new entry
    new_entry = DataEntry(
        question=question,
        answer=answer,
        category=category,
        content_hash=content_hash
    )

    try:
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({
            'id': new_entry.id,
            'question': new_entry.question,
            'answer': new_entry.answer,
            'category': new_entry.category,
            'created_at': new_entry.created_at.isoformat()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to add entry: {str(e)}'}), 500

@app.route('/browse')
def browse():
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    query = DataEntry.query
    if category:
        query = query.filter_by(category=category)

    pagination = query.order_by(DataEntry.created_at.desc()).paginate(page=page, per_page=per_page)
    entries = pagination.items

    return render_template('browse.html', entries=entries, pagination=pagination, category=category)

@app.route('/add', methods=['GET', 'POST'])
def add_form():
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        answer = request.form.get('answer', '').strip()
        category = request.form.get('category', '').lower()

        # Validate input
        if not question:
            flash('Question cannot be empty', 'error')
            return redirect(url_for('add_form'))

        if not answer:
            flash('Answer cannot be empty', 'error')
            return redirect(url_for('add_form'))

        if category not in ['riddle', 'joke', 'idiom']:
            flash('Invalid category', 'error')
            return redirect(url_for('add_form'))

        # Generate hash for deduplication
        content_hash = DataEntry.generate_hash(question, answer)

        # Check if entry already exists
        existing_entry = DataEntry.query.filter_by(content_hash=content_hash).first()
        if existing_entry:
            flash('This entry already exists in the database', 'error')
            return redirect(url_for('add_form'))

        # Create new entry
        new_entry = DataEntry(
            question=question,
            answer=answer,
            category=category,
            content_hash=content_hash
        )

        try:
            db.session.add(new_entry)
            db.session.commit()
            flash('Entry added successfully!', 'success')
            return redirect(url_for('browse'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding entry: {str(e)}', 'error')
            return redirect(url_for('add_form'))

    return render_template('add.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
