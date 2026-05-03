import os
from collections import Counter
from datetime import datetime
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from app.models import db, Event, Registration
from . import events_bp


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_recommended_events(user_id=None, current_event_id=None):
    """Return up to 4 recommended events, excluding already-registered ones."""
    exclude_ids = [current_event_id] if current_event_id else []

    if user_id:
        regs = Registration.query.filter_by(student_id=user_id).all()
        registered_ids = [r.event_id for r in regs]
        exclude_ids = list(set(exclude_ids + registered_ids))

        if regs:
            categories = [r.event.category for r in regs if r.event]
            if categories:
                top_cat = Counter(categories).most_common(1)[0][0]
                recs = Event.query.filter(
                    Event.category == top_cat,
                    ~Event.id.in_(exclude_ids) if exclude_ids else True
                ).limit(4).all()

                if len(recs) < 4:
                    existing_ids = exclude_ids + [e.id for e in recs]
                    recs += Event.query.filter(
                        ~Event.id.in_(existing_ids) if existing_ids else True
                    ).limit(4 - len(recs)).all()
                return recs

    query = Event.query
    if exclude_ids:
        query = query.filter(~Event.id.in_(exclude_ids))
    return query.order_by(Event.id.desc()).limit(4).all()


@events_bp.route('/')
def home():
    category = request.args.get('category')
    fee_type = request.args.get('fee_type')

    query = Event.query
    if category:
        query = query.filter_by(category=category)
    if fee_type == 'free':
        query = query.filter(Event.fee == 0)
    elif fee_type == 'paid':
        query = query.filter(Event.fee > 0)

    events = query.order_by(Event.starts_at.asc()).all()
    recommended = get_recommended_events(
        current_user.id if current_user.is_authenticated else None
    )
    return render_template('events/home.html', events=events, recommended=recommended)


@events_bp.route('/<int:event_id>')
def detail(event_id):
    event = Event.query.get_or_404(event_id)
    recommended = get_recommended_events(
        current_user.id if current_user.is_authenticated else None,
        current_event_id=event.id
    )
    return render_template('events/detail.html', event=event, recommended=recommended)


@events_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    if current_user.role not in ['organizer', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        starts_at = datetime.strptime(request.form.get('starts_at'), '%Y-%m-%dT%H:%M')
        ends_at = datetime.strptime(request.form.get('ends_at'), '%Y-%m-%dT%H:%M')
        capacity = int(request.form.get('capacity', 100))
        fee = float(request.form.get('fee', 0.0))
        category = request.form.get('category')
        venue = request.form.get('venue')
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        latitude = float(lat) if lat else None
        longitude = float(lon) if lon else None

        poster_url = None
        if 'poster' in request.files:
            file = request.files['poster']
            if file and allowed_file(file.filename):
                filename = secure_filename(
                    f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                )
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                poster_url = f"uploads/{filename}"

        event = Event(
            club_id=current_user.id,
            title=title,
            description=description,
            starts_at=starts_at,
            ends_at=ends_at,
            capacity=capacity,
            fee=fee,
            category=category,
            venue=venue,
            latitude=latitude,
            longitude=longitude,
            poster_url=poster_url
        )
        db.session.add(event)
        db.session.commit()
        flash('Event created successfully!', 'success')
        return redirect(url_for('events.detail', event_id=event.id))

    return render_template('events/create.html')


@events_bp.route('/<int:event_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    if request.method == 'POST':
        event.title = request.form.get('title')
        event.description = request.form.get('description')
        event.starts_at = datetime.strptime(request.form.get('starts_at'), '%Y-%m-%dT%H:%M')
        event.ends_at = datetime.strptime(request.form.get('ends_at'), '%Y-%m-%dT%H:%M')
        event.capacity = int(request.form.get('capacity', event.capacity))
        event.fee = float(request.form.get('fee', event.fee))
        event.category = request.form.get('category')
        event.venue = request.form.get('venue')
        lat = request.form.get('latitude')
        lon = request.form.get('longitude')
        event.latitude = float(lat) if lat else None
        event.longitude = float(lon) if lon else None

        if 'poster' in request.files:
            file = request.files['poster']
            if file and allowed_file(file.filename):
                filename = secure_filename(
                    f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
                )
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                event.poster_url = f"uploads/{filename}"

        db.session.commit()
        flash('Event updated successfully!', 'success')
        return redirect(url_for('events.detail', event_id=event.id))

    return render_template('events/edit.html', event=event)


@events_bp.route('/<int:event_id>/delete', methods=['POST'])
@login_required
def delete(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    db.session.delete(event)
    db.session.commit()
    flash('Event deleted successfully.', 'success')
    return redirect(url_for('events.home'))


@events_bp.route('/<int:event_id>/attendees')
@login_required
def attendees(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))
        
    status_filter = request.args.get('filter', 'all')
    
    query = Registration.query.filter_by(event_id=event_id)
    if status_filter == 'paid':
        query = query.filter_by(paid=True)
    elif status_filter == 'attended':
        query = query.filter_by(attended=True)
        
    registrations = query.order_by(Registration.created_at.desc()).all()
    
    return render_template('events/attendees.html', event=event, registrations=registrations, current_filter=status_filter)
