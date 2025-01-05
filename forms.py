from flask_wtf import FlaskForm
from wtforms import (
    StringField, SelectField, SubmitField, 
    DateField, TimeField, IntegerField
)
from wtforms.validators import DataRequired, Email, NumberRange

# --- Nutzer-Buchung in zwei Schritten ---
class BookTypeForm(FlaskForm):
    """Schritt 1: Terminart auswählen."""
    appointment_type = SelectField('Terminart', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Weiter')

class BookSlotForm(FlaskForm):
    """Schritt 2: Konkreten Termin-Slot + Name & E-Mail."""
    timeslot = SelectField('Freie Termine', coerce=str, validators=[DataRequired()])
    customer_name = StringField('Name', validators=[DataRequired()])
    customer_email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Termin buchen')

# --- Status-Abfrage ---
class StatusForm(FlaskForm):
    appointment_number = StringField('Termin Nummer', validators=[DataRequired()])
    submit = SubmitField('Status prüfen')

# --- Admin: Mehrere Tage auf einmal hinzufügen ---
class MultipleDaysForm(FlaskForm):
    """
    Statt jeden Tag einzeln hinzuzufügen, kann der Admin ein Start- 
    und Enddatum festlegen (z.B. 1.10. bis 5.10.) und eine einheitliche 
    Start- und Endzeit (z.B. 08:00 bis 16:00).
    """
    start_date = DateField('Startdatum', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Enddatum', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Startzeit (HH:MM)', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('Endzeit (HH:MM)', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Tage hinzufügen')

# --- Admin: Neue Terminart hinzufügen ---
class AppointmentTypeForm(FlaskForm):
    name = StringField('Terminart Name', validators=[DataRequired()])
    duration = IntegerField('Dauer (Minuten)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Terminart hinzufügen')
