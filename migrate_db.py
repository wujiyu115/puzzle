from app import app, db, DataEntry
import sqlite3
import os

def migrate_data():
    """
    Migrate existing data to the new schema with separate question and answer fields.
    This script should be run once after updating the model.
    """
    with app.app_context():
        # Check if the database exists
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if not os.path.exists(db_path):
            print(f"Database file {db_path} not found. Nothing to migrate.")
            return
        
        # Connect to the database directly to check schema
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the question and answer columns exist
        cursor.execute("PRAGMA table_info(data_entries)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'question' in columns and 'answer' in columns:
            print("Database already has question and answer columns. No migration needed.")
            conn.close()
            return
        
        # Add new columns if they don't exist
        if 'question' not in columns:
            cursor.execute("ALTER TABLE data_entries ADD COLUMN question TEXT")
        if 'answer' not in columns:
            cursor.execute("ALTER TABLE data_entries ADD COLUMN answer TEXT")
        
        # Fetch all entries
        cursor.execute("SELECT id, content, category FROM data_entries")
        entries = cursor.fetchall()
        
        # Update each entry
        for entry_id, content, category in entries:
            question = ""
            answer = ""
            
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
            
            # Update the entry
            cursor.execute(
                "UPDATE data_entries SET question = ?, answer = ? WHERE id = ?",
                (question, answer, entry_id)
            )
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print(f"Successfully migrated {len(entries)} entries to the new schema.")

if __name__ == "__main__":
    migrate_data()
