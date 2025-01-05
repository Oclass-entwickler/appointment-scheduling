from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Appointment, AppointmentType, AvailableDay
from forms import (
    BookTypeForm,
    BookSlotForm,
    StatusForm,
    AvailableDayForm,
    AppointmentTypeForm
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
#
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)


# --- Hilfsfunktion: Freie Slots berechnen ---
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
        # Alle Termine an diesem Tag laden
        day_appointments = Appointment.query.filter_by(date=day.date).all()

        # Start-/Endzeit in datetime kombinieren, um einfacher rechnen zu können
        current_start = datetime.combine(day.date, day.start_time)
        day_end = datetime.combine(day.date, day.end_time)
        slot_duration = timedelta(minutes=type_obj.duration)

        while current_start + slot_duration <= day_end:
            # Prüfen, ob current_start in Konflikt mit einem bestehenden Termin steht
            conflict = False
            for appt in day_appointments:
                appt_start = datetime.combine(appt.date, appt.time)
                appt_end = appt_start + timedelta(minutes=appt.type.duration)
                # Prüfen, ob sich Slots überschneiden
                if not (current_start + slot_duration <= appt_start or current_start >= appt_end):
                    conflict = True
                    break

            if not conflict:
                # Format: "YYYY-MM-DD HH:MM"
                slot_str = current_start.strftime('%Y-%m-%d %H:%M')
                free_slots.append(slot_str)

            # Zum nächsten Zeitslot gehen
            current_start += slot_duration

    return free_slots

# --- Initialer Datenbank-Setup ---
with app.app_context():
    db.create_all()

    # Beispiel: Terminarten hinzufügen, falls keine existieren
    if AppointmentType.query.count() == 0:
        standard_types = [
            {'name': 'Pass Antrag', 'duration': 30},
            {'name': 'Beglaubigen von Papier', 'duration': 20}
        ]
        for t in standard_types:
            db.session.add(AppointmentType(name=t['name'], duration=t['duration']))
        db.session.commit()

# --- Routen ---

@app.route('/')
def index():
    return render_template('index.html')

# Schritt 1: Terminart wählen
@app.route('/book', methods=['GET', 'POST'])
def book_select_type():
    form = BookTypeForm()
    # Liste aller Terminarten laden
    form.appointment_type.choices = [
        (t.id, t.name) for t in AppointmentType.query.order_by(AppointmentType.name.asc()).all()
    ]
    if form.validate_on_submit():
        # Weiter zu Schritt 2 und Terminart in URL übernehmen
        return redirect(url_for('book_select_slot', type_id=form.appointment_type.data))
    return render_template('book_type.html', form=form)

# Schritt 2: Freien Termin-Slot + Kontaktdaten eingeben
@app.route('/book/slot', methods=['GET', 'POST'])
def book_select_slot():
    type_id = request.args.get('type_id')
    if not type_id:
        flash('Bitte zuerst eine Terminart auswählen.', 'warning')
        return redirect(url_for('book_select_type'))

    # Verfügbare Slots berechnen
    free_slots = get_free_slots_for_type(type_id)
    if not free_slots:
        flash('Zurzeit sind keine freien Termine für diese Terminart verfügbar.', 'warning')
        return redirect(url_for('book_select_type'))

    form = BookSlotForm()
    # Dropdown mit allen freien Slots befüllen
    form.timeslot.choices = [(slot, slot) for slot in free_slots]

    if form.validate_on_submit():
        # Gewählten Slot auswerten (z.B. "2025-01-05 09:30")
        slot_str = form.timeslot.data
        try:
            slot_dt = datetime.strptime(slot_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('Ungültiger Termin-Slot ausgewählt.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

        # Eindeutige Termin-Nummer generieren
        last_appointment = Appointment.query.order_by(Appointment.appointment_number.desc()).first()
        next_number = last_appointment.appointment_number + 1 if last_appointment else 1

        # Neuen Termin anlegen
        new_appointment = Appointment(
            appointment_number=next_number,
            type_id=int(type_id),
            customer_name=form.customer_name.data,
            customer_email=form.customer_email.data,
            date=slot_dt.date(),
            time=slot_dt.time()
        )

        db.session.add(new_appointment)
        try:
            db.session.commit()
            flash(
                f"Termin erfolgreich gebucht! Ihre Termin Nummer ist {new_appointment.appointment_number} "
                f"am {slot_dt.date()} um {slot_dt.strftime('%H:%M')} Uhr.",
                'success'
            )
            return redirect(url_for('index'))
        except IntegrityError:
            db.session.rollback()
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

    return render_template('book_slot.html', form=form)

@app.route('/status', methods=['GET', 'POST'])
def check_status():
    form = StatusForm()
    if form.validate_on_submit():
        try:
            number = int(form.appointment_number.data)
            appointment = Appointment.query.filter_by(appointment_number=number).first()
            if appointment:
                return render_template('view_status.html', appointment=appointment)
            else:
                flash('Termin Nummer nicht gefunden.', 'warning')
        except ValueError:
            flash('Bitte geben Sie eine gültige Nummer ein.', 'danger')
    return render_template('check_status.html', form=form)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Vereinfachte Admin-Seite ohne Authentifizierung
    appointments = Appointment.query.order_by(Appointment.date.desc(), Appointment.time.asc()).all()
    types = AppointmentType.query.all()
    available_days = AvailableDay.query.order_by(AvailableDay.date.asc()).all()
    return render_template('admin.html', appointments=appointments, types=types, available_days=available_days)


@app.route('/admin/available_day/add', methods=['GET', 'POST'])
def add_available_day():
    form = AvailableDayForm()
    if form.validate_on_submit():
        # Überprüfen, ob das Datum bereits existiert
        existing_day = AvailableDay.query.filter_by(date=form.date.data).first()
        if existing_day:
            flash('Dieser Tag ist bereits als verfügbar festgelegt.', 'warning')
            return redirect(url_for('admin'))
        if form.start_time.data >= form.end_time.data:
            flash('Die Startzeit muss vor der Endzeit liegen.', 'danger')
            return redirect(url_for('add_available_day'))

        new_day = AvailableDay(
            date=form.date.data,
            start_time=form.start_time.data,
            end_time=form.end_time.data
        )
        db.session.add(new_day)
        try:
            db.session.commit()
            flash(f'Verfügbarer Tag {new_day.date} hinzugefügt.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('Ein Datenbankfehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
    return render_template('add_available_day.html', form=form)

@app.route('/admin/appointment_type/add', methods=['GET', 'POST'])
def add_appointment_type():
    form = AppointmentTypeForm()
    if form.validate_on_submit():
        # Prüfen, ob die Terminart existiert
        existing = AppointmentType.query.filter_by(name=form.name.data).first()
        if existing:
            flash('Diese Terminart existiert bereits.', 'warning')
            return redirect(url_for('admin'))
        new_type = AppointmentType(
            name=form.name.data,
            duration=form.duration.data
        )
        db.session.add(new_type)
        try:
            db.session.commit()
            flash(f'Terminart "{new_type.name}" hinzugefügt.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('Ein Datenbankfehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
    return render_template('add_appointment_type.html', form=form)

@app.route('/admin/reject/<int:appointment_id>', methods=['POST'])
def reject_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    if appointment.status != 'Abgelehnt':
        appointment.status = 'Abgelehnt'
        db.session.commit()
        flash(f'Termin {appointment.appointment_number} abgelehnt.', 'info')
    else:
        flash('Termin ist bereits abgelehnt.', 'warning')
    return redirect(url_for('admin'))


#########
if __name__ == '__main__':
    app.run(debug=True)
