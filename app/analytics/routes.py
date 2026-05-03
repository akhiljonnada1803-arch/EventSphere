import io
import pandas as pd
from flask import render_template, redirect, url_for, flash, request, current_app, send_file
from flask_login import current_user, login_required
from flask_mail import Message
from sqlalchemy import func
from app import mail
from app.models import db, Event, Registration, Payment, Feedback, Certificate
from app.utils.pdf_generator import create_certificate_pdf
from . import analytics_bp


@analytics_bp.route('/dashboard')
@login_required
def dashboard():
    if current_user.role not in ['organizer', 'admin']:
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    events = Event.query.filter_by(club_id=current_user.id).all()
    event_ids = [e.id for e in events]

    if not event_ids:
        return render_template('analytics/dashboard.html', stats=None, events=[])

    total_registrations = Registration.query.filter(
        Registration.event_id.in_(event_ids)
    ).count()
    attendance_count = Registration.query.filter(
        Registration.event_id.in_(event_ids),
        Registration.attended == True  # noqa: E712
    ).count()
    revenue = (
        db.session.query(func.sum(Payment.amount))
        .join(Registration)
        .filter(
            Registration.event_id.in_(event_ids),
            Payment.status == 'success'
        )
        .scalar() or 0.0
    )

    stats = {
        'total_registrations': total_registrations,
        'attendance_count': attendance_count,
        'revenue': revenue
    }
    return render_template('analytics/dashboard.html', stats=stats, events=events)


@analytics_bp.route('/<int:event_id>')
@login_required
def event_analytics(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    total_registrations = Registration.query.filter_by(event_id=event.id).count()
    attendance_count = Registration.query.filter_by(event_id=event.id, attended=True).count()
    revenue = (
        db.session.query(func.sum(Payment.amount))
        .join(Registration)
        .filter(Registration.event_id == event.id, Payment.status == 'success')
        .scalar() or 0.0
    )
    
    attendance_percentage = (attendance_count / total_registrations * 100) if total_registrations > 0 else 0

    stats = {
        'total_registrations': total_registrations,
        'attendance_count': attendance_count,
        'attendance_percentage': round(attendance_percentage, 1),
        'remaining_seats': event.remaining_spots,
        'revenue': revenue
    }
    
    # Chart Data: Registration over time (last 7 days)
    # For now, let's just provide some mock data for the graph to show we can use Chart.js
    # Real logic would group by date
    
    return render_template('analytics/event_dashboard.html', event=event, stats=stats)


@analytics_bp.route('/<int:event_id>/export')
@login_required
def export_attendees(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    export_type = request.args.get('type', 'registered') # registered, attended
    format_type = request.args.get('format', 'csv') # csv, excel

    query = Registration.query.filter_by(event_id=event_id)
    if export_type == 'attended':
        query = query.filter_by(attended=True)
    
    registrations = query.all()
    
    data = []
    for reg in registrations:
        data.append({
            'Name': reg.student.name,
            'Email': reg.student.email,
            'Phone': reg.phone,
            'College': reg.college,
            'Department': reg.department,
            'Team Name': reg.team_name,
            'Gender': reg.gender,
            'Paid': 'Yes' if reg.paid else 'No',
            'Attended': 'Yes' if reg.attended else 'No',
            'Registration Date': reg.created_at.strftime('%Y-%m-%d %H:%M')
        })

    if not data:
        flash('No data to export.', 'info')
        return redirect(url_for('events.attendees', event_id=event_id))

    df = pd.DataFrame(data)
    
    if format_type == 'excel':
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Attendees')
        output.seek(0)
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f"{event.title.replace(' ', '_')}_attendees.xlsx"
        )
    else:
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f"{event.title.replace(' ', '_')}_attendees.csv"
        )


@analytics_bp.route('/broadcast/<int:event_id>', methods=['GET', 'POST'])
@login_required
def broadcast(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        message_body = request.form.get('message')

        registrations = Registration.query.filter_by(event_id=event_id).all()
        emails = [r.student.email for r in registrations if r.student]

        if emails:
            try:
                with mail.connect() as conn:
                    for email in emails:
                        msg = Message(
                            subject,
                            sender=current_app.config['MAIL_USERNAME'],
                            recipients=[email]
                        )
                        msg.body = message_body
                        conn.send(msg)
                flash(f'Broadcast sent to {len(emails)} attendees!', 'success')
            except Exception as e:
                flash(f'Broadcast failed: {e}', 'error')
        else:
            flash('No attendees registered yet.', 'info')

        return redirect(url_for('analytics.dashboard'))

    return render_template('analytics/broadcast.html', event=event)


@analytics_bp.route('/feedback/<int:event_id>', methods=['GET', 'POST'])
@login_required
def submit_feedback(event_id):
    event = Event.query.get_or_404(event_id)

    registration = Registration.query.filter_by(
        event_id=event_id, student_id=current_user.id
    ).first()
    if not registration or not registration.attended:
        flash('You can only submit feedback for events you attended.', 'error')
        return redirect(url_for('events.detail', event_id=event_id))

    existing = Feedback.query.filter_by(
        event_id=event_id, student_id=current_user.id
    ).first()
    if existing:
        flash('You have already submitted feedback for this event.', 'info')
        return redirect(url_for('events.detail', event_id=event_id))

    if request.method == 'POST':
        rating = int(request.form.get('rating'))
        comment = request.form.get('comment')

        feedback = Feedback(
            event_id=event_id,
            student_id=current_user.id,
            rating=rating,
            comment=comment
        )
        db.session.add(feedback)
        db.session.commit()
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('events.detail', event_id=event_id))

    return render_template('analytics/feedback.html', event=event)


@analytics_bp.route('/download-certificate/<int:event_id>')
@login_required
def download_certificate(event_id):
    event = Event.query.get_or_404(event_id)
    registration = Registration.query.filter_by(
        event_id=event_id, student_id=current_user.id
    ).first()

    if not registration or not registration.attended:
        flash('You must attend the event to get a certificate.', 'error')
        return redirect(url_for('registrations.my_tickets'))

    cert = Certificate.query.filter_by(event_id=event_id, user_id=current_user.id).first()
    if cert:
        return redirect(url_for('static', filename=cert.file_path))

    pdf_path = create_certificate_pdf(current_user, event)
    cert = Certificate(event_id=event.id, user_id=current_user.id, file_path=pdf_path)
    db.session.add(cert)
    db.session.commit()

    return redirect(url_for('static', filename=pdf_path))


@analytics_bp.route('/send-certificates/<int:event_id>', methods=['POST'])
@login_required
def send_certificates(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.id != event.club_id and current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('events.home'))

    attendees = Registration.query.filter_by(event_id=event_id, attended=True).all()
    count = 0
    try:
        with mail.connect() as conn:
            for reg in attendees:
                user = reg.student
                cert = Certificate.query.filter_by(
                    event_id=event.id, user_id=user.id
                ).first()
                if not cert:
                    pdf_path = create_certificate_pdf(user, event)
                    cert = Certificate(
                        event_id=event.id, user_id=user.id, file_path=pdf_path
                    )
                    db.session.add(cert)
                    db.session.commit()

                msg = Message(
                    f"Your Certificate for {event.title}",
                    sender=current_app.config['MAIL_USERNAME'],
                    recipients=[user.email]
                )
                msg.body = (
                    f"Hello {user.name},\n\nThank you for attending {event.title}. "
                    f"Please find your certificate attached."
                )
                filepath = os.path.join(current_app.root_path, 'static', cert.file_path)
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as fp:
                        msg.attach(f"Certificate_{event.id}.pdf", "application/pdf", fp.read())
                conn.send(msg)
                count += 1
    except Exception as e:
        flash(f'Failed to send certificates: {e}', 'error')
        return redirect(url_for('analytics.dashboard'))

    flash(f'Sent {count} certificates to attendees!', 'success')
    return redirect(url_for('analytics.dashboard'))
