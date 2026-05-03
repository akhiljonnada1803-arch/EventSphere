import os
import uuid
import json
import qrcode
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import current_user, login_required
from flask_mail import Message
from app import mail
from app.models import db, Event, Registration
from . import registrations_bp


# ── Helpers ─────────────────────────────────────────────────────────────────

def generate_qr_code(token):
    """Generate a QR code PNG for *token* and return its static-relative path."""
    qrcodes_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'qrcodes')
    os.makedirs(qrcodes_dir, exist_ok=True)

    filename = f"qr_{token}.png"
    filepath = os.path.join(qrcodes_dir, filename)

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    img.save(filepath)

    return f"uploads/qrcodes/{filename}"


def send_ticket_email(user, event, registration):
    """Send registration confirmation with PDF ticket attached."""
    msg = Message(
        subject=f"Your Ticket for {event.title}",
        sender=current_app.config['MAIL_USERNAME'],
        recipients=[user.email]
    )
    msg.body = (
        f"Hello {user.name},\n\n"
        f"You are successfully registered for {event.title}!\n\n"
        f"Event Details:\n"
        f"Title: {event.title}\n"
        f"Date: {event.starts_at.strftime('%B %d, %Y')}\n"
        f"Time: {event.starts_at.strftime('%I:%M %p')}\n"
        f"Venue: {event.venue or 'EventSpheres Hub'}\n\n"
        f"Please find your official PDF ticket attached. Present the QR code on the ticket at the entrance.\n\n"
        f"See you there!"
    )

    from app.utils.pdf_generator import create_ticket_pdf
    pdf_path = create_ticket_pdf(registration, user, event, registration.qr_token)
    
    if pdf_path:
        filepath = os.path.join(current_app.root_path, 'static', pdf_path)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as fp:
                msg.attach(f"Ticket_{event.id}.pdf", "application/pdf", fp.read())

    try:
        mail.send(msg)
    except Exception as e:
        current_app.logger.warning(f"Failed to send ticket email: {e}")


# ── Routes ───────────────────────────────────────────────────────────────────

@registrations_bp.route('/event/<int:event_id>/register', methods=['POST'])
@login_required
def register(event_id):
    event = Event.query.get_or_404(event_id)

    existing = Registration.query.filter_by(
        event_id=event_id, student_id=current_user.id
    ).first()
    if existing:
        flash('You are already registered for this event.', 'info')
        return redirect(url_for('events.detail', event_id=event_id))

    is_group = request.form.get('is_group') == 'on'
    group_size = int(request.form.get('group_size', 1)) if is_group else 1

    group_members = None
    if is_group:
        members = [request.form.get(f'member_{i}') for i in range(1, group_size + 1)]
        group_members = json.dumps(members)

    if event.remaining_spots < group_size:
        flash(f'Sorry, only {event.remaining_spots} spots left.', 'error')
        return redirect(url_for('events.detail', event_id=event_id))

    phone = request.form.get('phone')
    college = request.form.get('college')
    department = request.form.get('department')
    team_name = request.form.get('team_name')
    gender = request.form.get('gender')

    if event.fee > 0:
        session['pending_registration'] = {
            'event_id': event_id,
            'is_group': is_group,
            'group_size': group_size,
            'group_members': group_members,
            'phone': phone,
            'college': college,
            'department': department,
            'team_name': team_name,
            'gender': gender
        }
        return redirect(url_for('payments.checkout', event_id=event.id))

    # Free event — register immediately
    token = str(uuid.uuid4())
    qr_path = generate_qr_code(token)

    registration = Registration(
        event_id=event.id,
        student_id=current_user.id,
        paid=True,
        qr_token=token,
        is_group=is_group,
        group_size=group_size,
        group_members=group_members,
        phone=phone,
        college=college,
        department=department,
        team_name=team_name,
        gender=gender
    )
    db.session.add(registration)
    db.session.commit()

    send_ticket_email(current_user, event, registration)
    flash('Successfully registered! Your PDF ticket has been sent to your email.', 'success')
    return redirect(url_for('events.detail', event_id=event.id))


@registrations_bp.route('/my-tickets')
@login_required
def my_tickets():
    registrations = (
        Registration.query
        .filter_by(student_id=current_user.id)
        .order_by(Registration.created_at.desc())
        .all()
    )
    return render_template('registrations/my_tickets.html', registrations=registrations)


@registrations_bp.route('/check-in/<int:event_id>', methods=['GET', 'POST'])
@login_required
def check_in(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    if request.method == 'POST':
        token = request.json.get('qr_token') if request.is_json else None
        if not token:
            return {'status': 'error', 'message': 'No token provided'}, 400

        reg = Registration.query.filter_by(event_id=event_id, qr_token=token).first()
        if not reg:
            return {'status': 'error', 'message': 'Invalid ticket'}, 404

        if reg.attended:
            return {'status': 'warning', 'message': 'Already checked in!'}, 200

        reg.attended = True
        db.session.commit()
        return {'status': 'success', 'message': f'Checked in {reg.student.name}'}, 200

    return render_template('registrations/check_in.html', event=event)

from datetime import datetime
from app.utils.pdf_generator import create_ticket_pdf, create_certificate_pdf

@registrations_bp.route('/tickets/download/<int:registration_id>')
@login_required
def download_ticket(registration_id):
    reg = Registration.query.get_or_404(registration_id)
    if reg.student_id != current_user.id and current_user.role not in ['organizer', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('registrations.my_tickets'))
        
    pdf_path = create_ticket_pdf(reg, reg.student, reg.event, reg.qr_token)
    return redirect(url_for('static', filename=pdf_path))

@registrations_bp.route('/certificates/download/<int:registration_id>')
@login_required
def download_certificate(registration_id):
    reg = Registration.query.get_or_404(registration_id)
    if reg.student_id != current_user.id and current_user.role not in ['organizer', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('registrations.my_tickets'))
        
    if not reg.attended:
        flash('Certificate is only available for participants who attended the event.', 'error')
        return redirect(url_for('registrations.my_tickets'))

    if reg.event.ends_at > datetime.utcnow():
        flash('Certificates will be available once the event ends.', 'error')
        return redirect(url_for('registrations.my_tickets'))
        
    pdf_path = create_certificate_pdf(reg.student, reg.event)
    return redirect(url_for('static', filename=pdf_path))
