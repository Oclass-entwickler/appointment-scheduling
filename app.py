from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Appointment, AppointmentType, AvailableDay
from forms import (
    BookTypeForm, BookSlotForm, StatusForm,
    MultipleDaysForm, AppointmentTypeForm
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# -- Hilfsfunktion: Alle freien Slots für eine Terminart --
def get_free_slots_for_type(appointment_type_id):
    """
    Ermittelt alle freien Zeitslots (Datum + Uhrzeit),
    die für die gegebene Terminart verfügbar sind.
    """
    type_obj = AppointmentType.query.get(appointment_type_id)
    if not type_obj:
        return []

    all_days = AvailableDay.query.order_by(AvailableDay.date.asc()).all()
    free_slots = []

    for day in all_days:
        # Alle Termine an diesem Tag
        day_appointments = Appointment.query.filter_by(date=day.date).all()

        # Start- und Endzeit in datetime
        current_start = datetime.combine(day.date, day.start_time)
        day_end = datetime.combine(day.date, day.end_time)
        slot_duration = timedelta(minutes=type_obj.duration)

        while current_start + slot_duration <= day_end:
            conflict = False
            for appt in day_appointments:
                appt_start = datetime.combine(appt.date, appt.time)
                appt_end = appt_start + timedelta(minutes=appt.type.duration)
                # Überschneidung?
                if not (current_start + slot_duration <= appt_start or current_start >= appt_end):
                    conflict = True
                    break

            if not conflict:
                # Format "YYYY-MM-DD HH:MM"
                slot_str = current_start.strftime('%Y-%m-%d %H:%M')
                free_slots.append(slot_str)

            current_start += slot_duration

    return free_slots

# -- Datenbank anlegen und ggf. Default-Daten einfügen --
with app.app_context():
    db.create_all()
    if AppointmentType.query.count() == 0:
        default_types = [
            {'name': 'Pass Antrag', 'duration': 30},
            {'name': 'Beglaubigen von Papieren', 'duration': 20}
        ]
        for t in default_types:
            db.session.add(AppointmentType(name=t['name'], duration=t['duration']))
        db.session.commit()

# --- Routen (User-Bereich) ---

@app.route('/')
def index():
    return render_template('index.html')

# 1. Schritt: Terminart auswählen
@app.route('/book', methods=['GET', 'POST'])
def book_select_type():
    form = BookTypeForm()
    form.appointment_type.choices = [
        (t.id, t.name) for t in AppointmentType.query.order_by(AppointmentType.name.asc()).all()
    ]
    if form.validate_on_submit():
        # Weiter zu Schritt 2
        return redirect(url_for('book_select_slot', type_id=form.appointment_type.data))
    return render_template('book_type.html', form=form)

# 2. Schritt: Konkreten Slot wählen + Kundendaten
@app.route('/book/slot', methods=['GET', 'POST'])
def book_select_slot():
    type_id = request.args.get('type_id')
    if not type_id:
        flash('Bitte zuerst eine Terminart auswählen.', 'warning')
        return redirect(url_for('book_select_type'))

    # Alle freien Slots berechnen
    free_slots = get_free_slots_for_type(int(type_id))
    if not free_slots:
        flash('Zurzeit sind keine freien Termine für diese Terminart verfügbar.', 'warning')
        return redirect(url_for('book_select_type'))

    form = BookSlotForm()
    form.timeslot.choices = [(slot, slot) for slot in free_slots]

    if form.validate_on_submit():
        slot_str = form.timeslot.data
        try:
            slot_dt = datetime.strptime(slot_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Ungültiger Termin-Slot ausgewählt.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

        # Eindeutige Termin-Nummer generieren
        last_appointment = Appointment.query.order_by(Appointment.appointment_number.desc()).first()
        next_number = last_appointment.appointment_number + 1 if last_appointment else 1

        new_appt = Appointment(
            appointment_number=next_number,
            type_id=int(type_id),
            customer_name=form.customer_name.data,
            customer_email=form.customer_email.data,
            date=slot_dt.date(),
            time=slot_dt.time()
        )
        db.session.add(new_appt)
        try:
            db.session.commit()
            flash(
                f"Termin erfolgreich gebucht! Ihre Termin Nummer ist {new_appt.appointment_number} "
                f"am {slot_dt.date()} um {slot_dt.strftime('%H:%M')} Uhr.",
                'success'
            )
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Ein Datenbankfehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

    return render_template('book_slot.html', form=form)

# Status abfragen
@app.route('/status', methods=['GET', 'POST'])
def check_status():
    form = StatusForm()
    if form.validate_on_submit():
        try:
            number = int(form.appointment_number.data)
            appt = Appointment.query.filter_by(appointment_number=number).first()
            if appt:
                return render_template('view_status.html', appointment=appt)
            else:
                flash('Termin Nummer nicht gefunden.', 'warning')
        except ValueError:
            flash('Bitte geben Sie eine gültige Nummer ein.', 'danger')
    return render_template('check_status.html', form=form)

# --- Admin-Bereich ---
@app.route('/admin')
def admin():
    # Zeigt direkt Formulare und Listen an ohne extra Seiten
    all_appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.asc()).all()
    all_types = AppointmentType.query.all()
    all_days = AvailableDay.query.order_by(AvailableDay.date.asc()).all()
    # Wir geben einfach mehrere Formulare auf einer Seite aus
    return render_template('admin.html',
                           appointments=all_appointments,
                           types=all_types,
                           days=all_days,
                           day_form=MultipleDaysForm(),
                           type_form=AppointmentTypeForm())

# Admin: Mehrere Tage auf einmal hinzufügen
@app.route('/admin/add_days', methods=['POST'])
def add_multiple_days():
    form = MultipleDaysForm()
    if form.validate_on_submit():
        start_date = form.start_date.data
        end_date = form.end_date.data
        s_time = form.start_time.data
        e_time = form.end_time.data

        if s_time >= e_time:
            flash('Startzeit muss vor Endzeit liegen.', 'danger')
            return redirect(url_for('admin'))
        if start_date > end_date:
            flash('Startdatum muss vor Enddatum liegen.', 'danger')
            return redirect(url_for('admin'))

        # Alle Tage von start_date bis end_date durchgehen
        current_day = start_date
        count_new = 0
        while current_day <= end_date:
            # Prüfen, ob Tag schon existiert
            existing = AvailableDay.query.filter_by(date=current_day).first()
            if not existing:
                new_day = AvailableDay(
                    date=current_day,
                    start_time=s_time,
                    end_time=e_time
                )
                db.session.add(new_day)
                count_new += 1
            current_day += timedelta(days=1)

        try:
            db.session.commit()
            flash(f'{count_new} Tag(e) wurden als verfügbar eingetragen.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ein Datenbankfehler ist aufgetreten.', 'danger')
    else:
        flash('Bitte alle Felder korrekt ausfüllen.', 'warning')
    return redirect(url_for('admin'))

# Admin: Neue Terminart hinzufügen
@app.route('/admin/add_type', methods=['POST'])
def add_appointment_type():
    form = AppointmentTypeForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        duration = form.duration.data
        # prüfen, ob die Terminart schon existiert
        existing = AppointmentType.query.filter_by(name=name).first()
        if existing:
            flash('Diese Terminart existiert bereits.', 'warning')
            return redirect(url_for('admin'))

        new_type = AppointmentType(name=name, duration=duration)
        db.session.add(new_type)
        try:
            db.session.commit()
            flash(f'Terminart "{name}" hinzugefügt.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ein Datenbankfehler ist aufgetreten.', 'danger')
    else:
        flash('Bitte alle Felder korrekt ausfüllen.', 'warning')
    return redirect(url_for('admin'))

# Admin: Termin ablehnen
@app.route('/admin/reject/<int:appointment_id>', methods=['POST'])
def reject_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.status != 'Abgelehnt':
        appt.status = 'Abgelehnt'
        db.session.commit()
        flash(f'Termin {appt.appointment_number} abgelehnt.', 'info')
    else:
        flash('Dieser Termin ist bereits abgelehnt.', 'warning')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
