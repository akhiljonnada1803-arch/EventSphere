import uuid
import razorpay
from flask import render_template, redirect, url_for, flash, request, current_app, session, jsonify
from flask_login import current_user, login_required
from app.models import db, Event, Registration, Payment
from app.registrations.routes import generate_qr_code, send_ticket_email
from . import payments_bp

def _razorpay_client():
    return razorpay.Client(auth=(
        current_app.config['RAZORPAY_KEY_ID'],
        current_app.config['RAZORPAY_KEY_SECRET']
    ))


@payments_bp.route('/payment/<int:event_id>')
@login_required
def checkout(event_id):
    current_app.logger.info(f"DEBUG: Entering checkout for event_id: {event_id}")
    event = Event.query.get_or_404(event_id)
    
    # Check session for group info (if coming from registration form)
    pending = session.get('pending_registration')
    if pending and pending.get('event_id') == event_id:
        group_size = pending.get('group_size', 1)
        current_app.logger.info(f"DEBUG: Found pending registration in session. Group size: {group_size}")
    else:
        group_size = 1
        current_app.logger.info("DEBUG: No pending registration found. Defaulting to group size 1")

    total_fee = event.fee * group_size

    if event.fee <= 0:
        current_app.logger.info("DEBUG: Event is free, redirecting to registration")
        return redirect(url_for('registrations.register', event_id=event_id))

    client = _razorpay_client()
    data = {
        "amount": int(total_fee * 100),  # paise
        "currency": "INR",
        "receipt": f"receipt_{event_id}_{current_user.id}_{uuid.uuid4().hex[:6]}"
    }

    try:
        order = client.order.create(data=data)
        current_app.logger.info(f"DEBUG: Razorpay order created: {order['id']}")
        return render_template(
            'payments/payment.html',
            event=event,
            order_id=order['id'],
            key_id=current_app.config['RAZORPAY_KEY_ID'],
            amount=data['amount'],
            total_fee=total_fee,
            group_size=group_size
        )
    except Exception as e:
        current_app.logger.error(f"DEBUG: Razorpay order creation failed: {str(e)}")
        flash(f'Payment initialisation failed: {str(e)}', 'error')
        return redirect(url_for('events.detail', event_id=event_id))


@payments_bp.route('/verify', methods=['POST'])
@login_required
def verify():
    current_app.logger.info("DEBUG: Entering payment verification")
    razorpay_payment_id = request.form.get('razorpay_payment_id')
    razorpay_order_id = request.form.get('razorpay_order_id')
    razorpay_signature = request.form.get('razorpay_signature')
    event_id = request.form.get('event_id', type=int)

    current_app.logger.info(f"DEBUG: Payment ID: {razorpay_payment_id}, Order ID: {razorpay_order_id}")

    event = Event.query.get_or_404(event_id)
    pending = session.get('pending_registration', {})
    
    if not razorpay_payment_id or not razorpay_signature:
        current_app.logger.warning("DEBUG: Missing payment details in verify")
        flash('Payment details missing.', 'error')
        return redirect(url_for('payments.checkout', event_id=event_id))

    client = _razorpay_client()

    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': razorpay_order_id,
            'razorpay_payment_id': razorpay_payment_id,
            'razorpay_signature': razorpay_signature
        })
        current_app.logger.info("DEBUG: Signature verification successful")

        token = str(uuid.uuid4())
        # qr_path no longer needed here as PDF generator handles it

        registration = Registration(
            event_id=event.id,
            student_id=current_user.id,
            paid=True,
            qr_token=token,
            is_group=pending.get('is_group', False),
            group_size=pending.get('group_size', 1),
            group_members=pending.get('group_members'),
            phone=pending.get('phone'),
            college=pending.get('college'),
            department=pending.get('department'),
            team_name=pending.get('team_name'),
            gender=pending.get('gender')
        )
        db.session.add(registration)
        db.session.flush()

        payment = Payment(
            registration_id=registration.id,
            amount=event.fee * registration.group_size,
            status='success',
            gateway_ref=razorpay_payment_id
        )
        db.session.add(payment)
        db.session.commit()
        current_app.logger.info(f"DEBUG: Registration and Payment records created. Reg ID: {registration.id}")

        session.pop('pending_registration', None)

        send_ticket_email(current_user, event, registration)
        flash('Payment successful! Your PDF ticket has been sent to your email.', 'success')
        return redirect(url_for('registrations.my_tickets'))

    except Exception as e:
        current_app.logger.error(f"DEBUG: Verification failed: {str(e)}")
        db.session.rollback()
        flash(f'Payment verification failed: {str(e)}', 'error')
        return redirect(url_for('payments.checkout', event_id=event_id))

# API Endpoints
@payments_bp.route('/api/create-order', methods=['POST'])
@login_required
def create_order_api():
    data = request.json
    event_id = data.get('event_id')
    group_size = data.get('group_size', 1)
    
    event = Event.query.get_or_404(event_id)
    total_fee = event.fee * group_size
    
    client = _razorpay_client()
    order_data = {
        "amount": int(total_fee * 100),
        "currency": "INR",
        "receipt": f"api_receipt_{event_id}_{current_user.id}"
    }
    
    try:
        order = client.order.create(data=order_data)
        return jsonify({
            'order_id': order['id'],
            'amount': order_data['amount'],
            'key_id': current_app.config['RAZORPAY_KEY_ID']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400
