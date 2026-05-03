import os
import qrcode
from io import BytesIO
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from flask import current_app

def create_ticket_pdf(registration, user, event, token):
    tickets_dir = os.path.join(current_app.root_path, 'static', 'tickets')
    os.makedirs(tickets_dir, exist_ok=True)
    
    filename = f"ticket_{registration.id}_{token}.pdf"
    filepath = os.path.join(tickets_dir, filename)
    
    # generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(token)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4
    
    # Draw background / ticket card
    c.setFillColorRGB(0.06, 0.09, 0.15) # dark theme bg
    c.rect(0, 0, width, height, fill=1)
    
    c.setFillColorRGB(0.1, 0.15, 0.25)
    c.roundRect(50, height - 350, width - 100, 300, 15, fill=1)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(80, height - 100, "EventSpheres Ticket")
    
    c.setFont("Helvetica-Bold", 20)
    c.drawString(80, height - 150, event.title)
    
    c.setFont("Helvetica", 14)
    c.drawString(80, height - 190, f"Attendee: {user.name}")
    c.drawString(80, height - 220, f"Date: {event.starts_at.strftime('%b %d, %Y - %I:%M %p')}")
    
    y_pos = height - 250
    if getattr(event, 'venue', None):
        c.drawString(80, y_pos, f"Venue: {event.venue}")
        y_pos -= 20
        if getattr(event, 'latitude', None) and getattr(event, 'longitude', None):
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.5, 0.5, 0.8)
            map_url = f"https://www.google.com/maps?q={event.latitude},{event.longitude}"
            c.drawString(80, y_pos, map_url)
            c.setFillColorRGB(1, 1, 1)
            c.setFont("Helvetica", 14)
            y_pos -= 10
        y_pos -= 20
        
    if registration.is_group:
        c.drawString(80, y_pos, f"Group Size: {registration.group_size}")
    else:
        c.drawString(80, y_pos, "Registration: Individual")
    
    y_pos -= 30
        
    c.setFont("Helvetica-Bold", 16)
    fee_text = "Free" if event.fee == 0 else f"Paid: Rs.{int(event.fee)}"
    c.drawString(80, y_pos, fee_text)
    
    qr_stream = BytesIO()
    qr_img.save(qr_stream, format='PNG')
    qr_stream.seek(0)
    c.drawImage(ImageReader(qr_stream), width - 220, y_pos - 10, width=140, height=140)
    
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.drawString(width - 200, y_pos - 30, f"ID: {token[:12]}")
    
    c.save()
    
    return f"tickets/{filename}"

def create_certificate_pdf(user, event):
    certs_dir = os.path.join(current_app.root_path, 'static', 'certificates')
    os.makedirs(certs_dir, exist_ok=True)
    
    filename = f"cert_{user.id}_{event.id}.pdf"
    filepath = os.path.join(certs_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=landscape(A4))
    width, height = landscape(A4)
    
    c.setFillColorRGB(0.06, 0.09, 0.15)
    c.rect(0, 0, width, height, fill=1)
    
    c.setLineWidth(5)
    c.setStrokeColorRGB(0.39, 0.4, 0.95) # indigo-500
    c.rect(30, 30, width - 60, height - 60)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(width / 2, height - 120, "Certificate of Participation")
    
    c.setFillColorRGB(0.8, 0.8, 0.8)
    c.setFont("Helvetica", 18)
    c.drawCentredString(width / 2, height - 180, "This is to certify that")
    
    c.setFillColorRGB(0.39, 0.4, 0.95)
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(width / 2, height - 240, user.name)
    
    c.setFillColorRGB(0.8, 0.8, 0.8)
    c.setFont("Helvetica", 16)
    c.drawCentredString(width / 2, height - 290, "has successfully participated in the event")
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width / 2, height - 340, event.title)
    
    c.setFillColorRGB(0.8, 0.8, 0.8)
    c.setFont("Helvetica", 14)
    c.drawCentredString(width / 2, height - 380, f"held on {event.starts_at.strftime('%B %d, %Y')}")
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica", 12)
    c.drawString(150, 120, "_________________________")
    c.drawString(150, 95, event.organizer.name)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawString(150, 80, "Event Organizer")
    
    c.setFillColorRGB(1, 1, 1)
    c.drawString(width - 350, 120, "_________________________")
    c.drawString(width - 350, 95, "EventSpheres Platform")
    
    c.save()
    
    return f"certificates/{filename}"
