from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Appointment, AppointmentType, RecurringDay, ExcludedDay
from forms import (
    BookTypeForm, BookSlotForm, StatusForm,
    RecurringDayForm, ExcludedDayForm, AppointmentTypeForm
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date, time

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# -----------------------------------
# Hilfsfunktionen
# -----------------------------------

def generate_slots_for_day(day_date, recurring_day_obj, duration_minutes):
    """
    Erzeugt alle möglichen Zeitslots für einen einzelnen Tag (day_date),
    basierend auf einem RecurringDay-Eintrag und der Dauer der Terminart in Minuten.
    Berücksichtigt eine optionale Pause (break_start/break_end).
    """
    slots = []
    slot_length = timedelta(minutes=duration_minutes)

    day_start = datetime.combine(day_date, recurring_day_obj.start_time)
    day_end = datetime.combine(day_date, recurring_day_obj.end_time)

    # Pausen
    break_start_dt = None
    break_end_dt = None
    if recurring_day_obj.break_start and recurring_day_obj.break_end:
        break_start_dt = datetime.combine(day_date, recurring_day_obj.break_start)
        break_end_dt = datetime.combine(day_date, recurring_day_obj.break_end)
        # Wenn Pausenangabe ungültig (break_start >= break_end), ignorieren wir sie
        if break_start_dt >= break_end_dt:
            break_start_dt = None
            break_end_dt = None

    current_start = day_start
    while current_start + slot_length <= day_end:
        # Prüfen, ob Zeit in die Pause fällt
        in_break = False
        if break_start_dt and break_end_dt:
            if not (current_start + slot_length <= break_start_dt or current_start >= break_end_dt):
                in_break = True

        if not in_break:
            slots.append(current_start)
        current_start += slot_length

    return slots

def get_free_slots_for_type(appointment_type_id, look_ahead_days=60):
    """
    Sucht in den kommenden `look_ahead_days` Tagen nach freien Slots für
    die angegebene Terminart. Berücksichtigt:
    - RecurringDay (mit day_of_week, start_date, end_date)
    - ExcludedDay
    - Bereits gebuchte Termine
    - Wochenende (Sa/So) wird übersprungen
    """
    type_obj = AppointmentType.query.get(appointment_type_id)
    if not type_obj:
        return []

    today = date.today()
    end_date = today + timedelta(days=look_ahead_days)
    free_slots = []

    # Alle RecurringDay-Einträge laden
    recurring_days = RecurringDay.query.all()

    # Einmalige Ausschlusstage sammeln
    excluded = {excl.date for excl in ExcludedDay.query.all()}

    # Gebuchte Termine im Zeitraum
    booked_appointments = Appointment.query.filter(
        Appointment.date >= today,
        Appointment.date <= end_date
    ).all()

    #booked_map[datum] = [(start_dt, end_dt), ...]
    booked_map = {}
    for appt in booked_appointments:
        appt_start = datetime.combine(appt.date, appt.time)
        appt_end = appt_start + timedelta(minutes=appt.type.duration)
        booked_map.setdefault(appt.date, []).append((appt_start, appt_end))

    # Für jeden Tag von heute bis end_date
    for single_day in (today + timedelta(n) for n in range((end_date - today).days + 1)):
        dow = single_day.weekday()  # 0=Montag, 6=Sonntag

        # Ausschlusstag oder Wochenende?
        if single_day in excluded:
            continue
        if dow > 4:  # Samstag(5) oder Sonntag(6)
            continue

        # Alle RecurringDay-Regeln durchsuchen, die:
        # 1. denselben Wochentag haben
        # 2. single_day >= start_date und single_day <= end_date
        
        day_matches = [
            r for r in recurring_days
            if r.day_of_week == dow
            and r.start_date <= single_day <= r.end_date
        ]
        if not day_matches:
            continue

        # Für jede passende Regel generieren wir Slots und filtern gebuchte
        for rec in day_matches:
            daily_slots = generate_slots_for_day(single_day, rec, type_obj.duration)

            valid_slots = []
            for slot_start_dt in daily_slots:
                slot_end_dt = slot_start_dt + timedelta(minutes=type_obj.duration)
                # Prüfen, ob Überschneidung mit bereits gebuchten Terminen
                conflicts = False
                for (booked_start, booked_end) in booked_map.get(single_day, []):
                    if not (slot_end_dt <= booked_start or slot_start_dt >= booked_end):
                        conflicts = True
                        break
                if not conflicts:
                    valid_slots.append(slot_start_dt.strftime('%Y-%m-%d %H:%M'))

            free_slots.extend(valid_slots)

    return sorted(free_slots)

# --------------------------------------
# Initialer DB-Setup
# --------------------------------------
with app.app_context():
    db.create_all()
    # Beispiel: Standard-Terminarten hinzufügen, falls keine existieren
    if AppointmentType.query.count() == 0:
        standard_types = [
            {'name': 'Pass Antrag', 'duration': 30},
            {'name': 'Beglaubigen von Papier', 'duration': 20}
        ]
        for st in standard_types:
            db.session.add(AppointmentType(name=st['name'], duration=st['duration']))
        db.session.commit()

# -----------------------------------
# Routen
# -----------------------------------

@app.route('/')
def index():
    return render_template('index.html')

# Schritt 1: Terminart wählen
@app.route('/book', methods=['GET', 'POST'])
def book_select_type():
    form = BookTypeForm()
    form.appointment_type.choices = [
        (t.id, t.name) for t in AppointmentType.query.order_by(AppointmentType.name.asc()).all()
    ]
    if form.validate_on_submit():
        return redirect(url_for('book_select_slot', type_id=form.appointment_type.data))
    return render_template('book_type.html', form=form)

# Schritt 2: Freien Termin-Slot + Kontaktdaten
@app.route('/book/slot', methods=['GET', 'POST'])
def book_select_slot():
    type_id = request.args.get('type_id')
    if not type_id:
        flash('Bitte zuerst eine Terminart auswählen.', 'warning')
        return redirect(url_for('book_select_type'))

    free_slots = get_free_slots_for_type(type_id)
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

        # Terminnummer generieren
        last_appointment = Appointment.query.order_by(Appointment.appointment_number.desc()).first()
        next_number = last_appointment.appointment_number + 1 if last_appointment else 1

        # Termin speichern
        new_appointment = Appointment(
            appointment_number=next_number,
            type_id=int(type_id),
            customer_name=form.customer_name.data,
            customer_email=form.customer_email.data,
            birth_date=form.birth_date.data,
            date=slot_dt.date(),
            time=slot_dt.time()
        )
        db.session.add(new_appointment)
        try:
            db.session.commit()

            # Nachricht abrufen
            appointment_type = AppointmentType.query.get(int(type_id))
            notification_message = appointment_type.notification_message if appointment_type else ""

            flash(
                f"Termin erfolgreich gebucht! Ihre Termin Nummer ist {new_appointment.appointment_number} "
                f"am {slot_dt.strftime('%Y-%m-%d')} um {slot_dt.strftime('%H:%M')} Uhr.",
                'success'
            )
            return render_template('booking_success.html',
                                   appointment=new_appointment,
                                   notification_message=notification_message)
        except IntegrityError:
            db.session.rollback()
            flash('Ein Fehler ist aufgetreten. Bitte versuchen Sie es erneut.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

    return render_template('book_slot.html', form=form)




@app.route('/status', methods=['GET', 'POST'])
def check_status():
    form = StatusForm()
    if form.validate_on_submit():
        name = form.customer_name.data.strip().lower()
        number = form.appointment_number.data.strip()
        birth_date = form.birth_date.data

        try:
            appointment = Appointment.query.filter(
                db.func.lower(Appointment.customer_name) == name,
                Appointment.appointment_number == int(number),
                Appointment.birth_date == birth_date
            ).first()

            if appointment:
                return render_template('view_status.html', appointment=appointment)
            else:
                flash('Kein Termin gefunden. Bitte überprüfen Sie die Angaben.', 'warning')
        except ValueError:
            flash('Ungültige Eingabe. Bitte geben Sie die Daten korrekt ein.', 'danger')

    return render_template('check_status.html', form=form)

# --- Admin-Bereich ---

# Admin-Bereich
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    search_name = request.args.get('search', '').strip().lower()
    appointments_query = Appointment.query

    if search_name:
        appointments_query = appointments_query.filter(
            db.func.lower(Appointment.customer_name).contains(search_name)
        )

    appointments = appointments_query.order_by(Appointment.date.desc(), Appointment.time.asc()).all()
    types = AppointmentType.query.all()
    recurring_days = RecurringDay.query.order_by(RecurringDay.day_of_week.asc()).all()
    excluded_days = ExcludedDay.query.order_by(ExcludedDay.date.asc()).all()

    return render_template(
        'admin.html',
        appointments=appointments,
        types=types,
        recurring_days=recurring_days,
        excluded_days=excluded_days,
        search_name=search_name
    )


# Termin löschen
@app.route('/admin/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash(f'Termin mit Nummer {appointment.appointment_number} wurde gelöscht.', 'info')
    return redirect(url_for('admin'))


@app.route('/admin/recurring_day/add', methods=['GET', 'POST'])
def add_recurring_day():
    form = RecurringDayForm()
    if form.validate_on_submit():
        start_t = form.start_time.data
        end_t = form.end_time.data
        b_start = form.break_start.data
        b_end = form.break_end.data
        start_d = form.start_date.data
        end_d = form.end_date.data

        # Validierung: start_time < end_time
        if start_t >= end_t:
            flash('Startzeit muss vor Endzeit liegen.', 'danger')
            return redirect(url_for('add_recurring_day'))

        # Validierung: start_date <= end_date
        if start_d > end_d:
            flash('Startdatum muss vor (oder gleich) Enddatum liegen.', 'danger')
            return redirect(url_for('add_recurring_day'))

        # Für jeden ausgewählten Wochentag wird ein Eintrag angelegt
        for day_str in form.days_of_week.data:
            day_of_week = int(day_str)
            rd = RecurringDay(
                day_of_week=day_of_week,
                start_date=start_d,
                end_date=end_d,
                start_time=start_t,
                end_time=end_t,
                break_start=b_start,
                break_end=b_end
            )
            db.session.add(rd)

        try:
            db.session.commit()
            flash('Wiederkehrende Wochentag(e) erfolgreich angelegt.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('Datenbankfehler. Vielleicht gibt es einen Konflikt.', 'danger')
    return render_template('add_recurring_day.html', form=form)

@app.route('/admin/excluded_day/add', methods=['GET', 'POST'])
def add_excluded_day():
    form = ExcludedDayForm()
    if form.validate_on_submit():
        new_ex = ExcludedDay(
            date=form.date.data,
            reason=form.reason.data or ''
        )
        db.session.add(new_ex)
        try:
            db.session.commit()
            flash('Ausschlusstag hinzugefügt.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('Dieser Tag ist bereits ausgeschlossen.', 'danger')
    return render_template('add_excluded_day.html', form=form)

@app.route('/admin/appointment_type/add', methods=['GET', 'POST'])
def add_appointment_type():
    form = AppointmentTypeForm()
    if form.validate_on_submit():
        existing = AppointmentType.query.filter_by(name=form.name.data).first()
        if existing:
            flash('Diese Terminart existiert bereits.', 'warning')
            return redirect(url_for('admin'))

        new_type = AppointmentType(
            name=form.name.data,
            duration=form.duration.data,
            notification_message=form.notification_message.data
        )
        db.session.add(new_type)
        try:
            db.session.commit()
            flash(f'Terminart "{new_type.name}" hinzugefügt.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('Datenbankfehler. Bitte erneut versuchen.', 'danger')
    return render_template('add_appointment_type.html', form=form)


@app.route('/admin/reject/<int:appointment_id>', methods=['POST'])
def reject_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.status != 'Abgelehnt':
        appt.status = 'Abgelehnt'
        db.session.commit()
        flash(f'Termin {appt.appointment_number} abgelehnt.', 'info')
    else:
        flash('Termin ist bereits abgelehnt.', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/recurring_day/delete/<int:rd_id>', methods=['POST'])
def delete_recurring_day(rd_id):
    rd = RecurringDay.query.get_or_404(rd_id)
    db.session.delete(rd)
    db.session.commit()
    flash('Wiederkehrender Tag gelöscht.', 'info')
    return redirect(url_for('admin'))

@app.route('/admin/excluded_day/delete/<int:ex_id>', methods=['POST'])
def delete_excluded_day(ex_id):
    ex = ExcludedDay.query.get_or_404(ex_id)
    db.session.delete(ex)
    db.session.commit()
    flash('Ausschlusstag gelöscht.', 'info')
    return redirect(url_for('admin'))

if __name__ == '__main__':
    app.run(debug=True)
