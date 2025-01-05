from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time

db = SQLAlchemy()

class AppointmentType(db.Model):
    """
    Repräsentiert eine Terminart, z.B. 'Pass Antrag' mit einer festen Dauer in Minuten.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    duration = db.Column(db.Integer, nullable=False)  # Dauer in Minuten

    def __repr__(self):
        return f"<AppointmentType {self.name}>"

class AvailableDay(db.Model):
    """
    Repräsentiert einen Tag, an dem Termine vergeben werden können,
    inklusive Start- und Endzeit.
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    def __repr__(self):
        return f"<AvailableDay {self.date}>"

class Appointment(db.Model):
    """
    Repräsentiert einen gebuchten Termin mit einer eindeutigen Nummer, 
    Terminart, Name, E-Mail, Datum und Uhrzeit.
    """
    id = db.Column(db.Integer, primary_key=True)
    appointment_number = db.Column(db.Integer, unique=True, nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Angemeldet')  # Angemeldet, Abgelehnt

    type = db.relationship('AppointmentType', backref=db.backref('appointments', lazy=True))

    def __repr__(self):
        return f"<Appointment {self.appointment_number} - {self.customer_name}>"
