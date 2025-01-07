from flask_wtf import FlaskForm
from wtforms import (
    StringField, SelectField, SelectMultipleField,
    TimeField, DateField, IntegerField, SubmitField, widgets
)
from wtforms.validators import DataRequired, Email, NumberRange

class MultiCheckboxField(SelectMultipleField):
    """
    Ein Mehrfachauswahlfeld für Wochentage (z.B. Montag, Dienstag, etc.).
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class BookTypeForm(FlaskForm):
    """
    Schritt 1: Terminart auswählen.
    """
    appointment_type = SelectField('Terminart', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Weiter')

class BookSlotForm(FlaskForm):
    """
    Schritt 2: Konkreten Slot (Datum + Uhrzeit) auswählen + Nutzerdetails eingeben.
    """
    timeslot = SelectField('Freie Termine', coerce=str, validators=[DataRequired()])
    customer_name = StringField('Name', validators=[DataRequired()])
    customer_email = StringField('Email', validators=[DataRequired(), Email()])
    birth_date = DateField('Geburtsdatum', format='%Y-%m-%d', validators=[DataRequired()])  # Geburtsdatum
    submit = SubmitField('Termin buchen')

class StatusForm(FlaskForm):
    appointment_number = StringField('Termin Nummer', validators=[DataRequired()])
    submit = SubmitField('Status prüfen')

class RecurringDayForm(FlaskForm):
    """
    Formular für das Hinzufügen mehrerer Wochentage (checkbox) + Datum-Beginn + Datum-Ende
    + Start-/Endzeit + optionaler Pause.
    """
    days_of_week = MultiCheckboxField(
        'Wochentag(e)',
        choices=[
            ('0', 'Montag'),
            ('1', 'Dienstag'),
            ('2', 'Mittwoch'),
            ('3', 'Donnerstag'),
            ('4', 'Freitag')
        ],
        validators=[DataRequired()]
    )
    start_date = DateField('Gültig ab (Datum)', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('Gültig bis (Datum)', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('Startzeit', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('Endzeit', format='%H:%M', validators=[DataRequired()])
    break_start = TimeField('Pausen-Beginn', format='%H:%M')
    break_end = TimeField('Pausen-Ende', format='%H:%M')
    submit = SubmitField('Speichern')

class ExcludedDayForm(FlaskForm):
    date = DateField('Datum', format='%Y-%m-%d', validators=[DataRequired()])
    reason = StringField('Grund (optional)')
    submit = SubmitField('Ausschlusstag hinzufügen')

from wtforms import TextAreaField

class AppointmentTypeForm(FlaskForm):
    name = StringField('Terminart Name', validators=[DataRequired()])
    duration = IntegerField('Dauer (Minuten)', validators=[DataRequired(), NumberRange(min=1)])
    notification_message = TextAreaField('Benachrichtigung (optional)')
    submit = SubmitField('Terminart hinzufügen')



class StatusForm(FlaskForm):
    customer_name = StringField('Name', validators=[DataRequired()])
    appointment_number = StringField('Termin Nummer', validators=[DataRequired()])
    birth_date = DateField('Geburtsdatum (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Status prüfen')
