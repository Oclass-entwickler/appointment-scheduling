from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time

db = SQLAlchemy()

class AppointmentType(db.Model):
    """
    Repräsentiert eine Terminart, z. B. 'Pass Antrag'.
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    duration = db.Column(db.Integer, nullable=False)  # Dauer in Minuten
    notification_message = db.Column(db.Text, nullable=True)  # Nachricht für die Terminart

    def __repr__(self):
        return f"<AppointmentType {self.name}>"


class RecurringDay(db.Model):
    """
    Ein wiederkehrender Tag (z.B. Montag-Freitag) mit:
    - day_of_week (0=Montag, ..., 4=Freitag)
    - gültig von start_date bis end_date
    - Start-/Endzeit
    - optionalem Pausenintervall (break_start, break_end)
    """
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Montag, 1=Dienstag, ... 4=Freitag
    start_date = db.Column(db.Date, nullable=False)      # Ab welchem Datum gilt diese Regel?
    end_date = db.Column(db.Date, nullable=False)        # Bis zu welchem Datum gilt diese Regel?
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    break_start = db.Column(db.Time, nullable=True)
    break_end = db.Column(db.Time, nullable=True)

    def __repr__(self):
        return (f"<RecurringDay Wochentag={self.day_of_week}, "
                f"{self.start_date} - {self.end_date}>")

class ExcludedDay(db.Model):
    """
    Ein einmaliger Ausschlusstag (Feiertag, Betriebsferien o.ä.).
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    reason = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f"<ExcludedDay {self.date} - {self.reason}>"

class Appointment(db.Model):
    """
    Gebuchter Termin:
    - Eindeutige Termin-Nummer
    - Terminart
    - Name/E-Mail
    - Geburtsdatum
    - Datum/Uhrzeit
    - Status (z. B. 'Angemeldet')
    """
    id = db.Column(db.Integer, primary_key=True)
    appointment_number = db.Column(db.Integer, unique=True, nullable=False)
    type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_email = db.Column(db.String(100), nullable=False)
    birth_date = db.Column(db.Date, nullable=False)  # Neues Feld für Geburtsdatum
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default='Angemeldet')

    type = db.relationship('AppointmentType', backref=db.backref('appointments', lazy=True))

    def __repr__(self):
        return f"<Appointment {self.appointment_number} - {self.customer_name}>"
