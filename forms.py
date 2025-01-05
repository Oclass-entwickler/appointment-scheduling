from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, DateField, TimeField, IntegerField
from wtforms.validators import DataRequired, Email, NumberRange

class BookTypeForm(FlaskForm):
    """
    Schritt 1: Nutzer wählt eine Terminart aus.
    """
    appointment_type = SelectField('Terminart', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Weiter')

class BookSlotForm(FlaskForm):
    """
    Schritt 2: Nutzer sieht alle möglichen Zeitslots für die gewählte Terminart
    und wählt einen aus. Zusätzlich gibt er Name und E-Mail an.
    """
    timeslot = SelectField('Freie Termine', coerce=str, validators=[DataRequired()])
    customer_name = StringField('Name', validators=[DataRequired()])
    customer_email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Termin buchen')

class StatusForm(FlaskForm):
    appointment_number = StringField('Termin Nummer', validators=[DataRequired()])
    submit = SubmitField('Status prüfen')

class AvailableDayForm(FlaskForm):
    date = DateField('Datum', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Startzeit (HH:MM)', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('Endzeit (HH:MM)', format='%H:%M', validators=[DataRequired()])
    submit = SubmitField('Verfügbaren Tag hinzufügen')

class AppointmentTypeForm(FlaskForm):
    name = StringField('Terminart Name', validators=[DataRequired()])
    duration = IntegerField('Dauer (Minuten)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Terminart hinzufügen')
