from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# Extensions defined here to avoid circular imports
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, organizer, admin

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    club_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    poster_url = db.Column(db.String(255), nullable=True)
    starts_at = db.Column(db.DateTime, nullable=False)
    ends_at = db.Column(db.DateTime, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=100)
    fee = db.Column(db.Float, nullable=False, default=0.0)
    category = db.Column(db.String(50), nullable=False)  # workshop, fest, hackathon
    
    venue = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    organizer = db.relationship('User', backref=db.backref('organized_events', lazy=True))

    @property
    def remaining_spots(self):
        registered_count = db.session.query(db.func.sum(Registration.group_size)).filter(Registration.event_id == self.id).scalar() or 0
        return max(0, self.capacity - registered_count)


class Registration(db.Model):
    __tablename__ = 'registrations'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    paid = db.Column(db.Boolean, default=False)
    qr_token = db.Column(db.String(100), unique=True, nullable=False)
    attended = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Attendee Details
    phone = db.Column(db.String(20), nullable=True)
    college = db.Column(db.String(150), nullable=True)
    department = db.Column(db.String(100), nullable=True)
    team_name = db.Column(db.String(100), nullable=True)
    gender = db.Column(db.String(20), nullable=True)

    # Group registration fields
    is_group = db.Column(db.Boolean, default=False)
    group_size = db.Column(db.Integer, default=1)
    group_members = db.Column(db.Text, nullable=True)  # JSON string of members

    event = db.relationship('Event', backref=db.backref('registrations', lazy=True))
    student = db.relationship('User', backref=db.backref('registrations', lazy=True))


class Payment(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(db.Integer, db.ForeignKey('registrations.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, success, failed
    gateway_ref = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    registration = db.relationship('Registration', backref=db.backref('payment', uselist=False))


class Feedback(db.Model):
    __tablename__ = 'feedback'
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship('Event', backref=db.backref('feedback', lazy=True))
    student = db.relationship('User', backref=db.backref('feedback', lazy=True))


class Certificate(db.Model):
    __tablename__ = 'certificates'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('certificates', lazy=True))
    event = db.relationship('Event', backref=db.backref('certificates', lazy=True))
