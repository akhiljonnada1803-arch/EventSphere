import sqlite3

conn = sqlite3.connect('events.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE events ADD COLUMN venue VARCHAR(200)")
    cursor.execute("ALTER TABLE events ADD COLUMN latitude FLOAT")
    cursor.execute("ALTER TABLE events ADD COLUMN longitude FLOAT")
    print("Added venue fields to events table.")
except sqlite3.OperationalError as e:
    print(f"Error adding events columns: {e}")

try:
    cursor.execute("ALTER TABLE registrations ADD COLUMN phone VARCHAR(20)")
    cursor.execute("ALTER TABLE registrations ADD COLUMN college VARCHAR(150)")
    cursor.execute("ALTER TABLE registrations ADD COLUMN department VARCHAR(100)")
    cursor.execute("ALTER TABLE registrations ADD COLUMN team_name VARCHAR(100)")
    cursor.execute("ALTER TABLE registrations ADD COLUMN gender VARCHAR(20)")
    print("Added attendee details to registrations table.")
except sqlite3.OperationalError as e:
    print(f"Error adding attendee details: {e}")

conn.commit()
conn.close()

from app import create_app
from app.models import db

app = create_app()
with app.app_context():
    db.create_all()
    print("Created any missing tables (like certificates).")
