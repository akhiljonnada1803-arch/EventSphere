"""
seed.py — Populate the database with sample data.

Run once after deployment:
    python seed.py
"""
from datetime import datetime, timedelta
from app import create_app
from app.models import db, User, Event

app = create_app()

with app.app_context():
    db.create_all()

    if User.query.first():
        print("Database already seeded — skipping.")
    else:
        print("Seeding database...")

        admin = User(name='Admin EventSpheres', email='admin@eventspheres.com', role='admin')
        admin.set_password('password123')

        organizer = User(name='John Organizer', email='organizer@eventspheres.com', role='organizer')
        organizer.set_password('password123')

        student = User(name='Alex Student', email='alex@eventspheres.com', role='student')
        student.set_password('password123')

        db.session.add_all([admin, organizer, student])
        db.session.commit()

        now = datetime.utcnow()

        events = [
            Event(
                club_id=organizer.id,
                title='NextGen Web3 Hackathon',
                description='A 48-hour coding marathon to solve real-world problems using Web3.',
                starts_at=now + timedelta(days=5),
                ends_at=now + timedelta(days=7),
                capacity=150, fee=0.0, category='hackathon'
            ),
            Event(
                club_id=organizer.id,
                title='AI & Cloud Security Workshop',
                description='Build secure AI apps and protect cloud infrastructure.',
                starts_at=now + timedelta(days=2),
                ends_at=now + timedelta(days=2, hours=4),
                capacity=50, fee=50.0, category='workshop'
            ),
            Event(
                club_id=admin.id,
                title='Global Tech Conference 2026',
                description='Networking, tech talks, and innovation showcases.',
                starts_at=now + timedelta(days=14),
                ends_at=now + timedelta(days=15),
                capacity=500, fee=150.0, category='fest'
            ),
        ]

        db.session.add_all(events)
        db.session.commit()
        print("Database seeded successfully!")
        print("\nSample credentials:")
        print("  admin@eventspheres.com     / password123  (admin)")
        print("  organizer@eventspheres.com / password123  (organizer)")
        print("  alex@eventspheres.com      / password123  (student)")
