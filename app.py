from flask import Flask, render_template, redirect, url_for, flash, request
from config import Config
from models import db, Appointment, AppointmentType, RecurringDay, ExcludedDay
from forms import (
    BookTypeForm, BookSlotForm, StatusForm,
    RecurringDayForm, ExcludedDayForm, AppointmentTypeForm
)
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, date, time
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.from_object(Config)
mail = Mail(app) 
db.init_app(app)

# -----------------------------------
# الدوال المساعدة
# -----------------------------------

def generate_slots_for_day(day_date, recurring_day_obj, duration_minutes):
    """
    ينشئ جميع الفترات الزمنية الممكنة ليوم واحد (day_date)،
    بناءً على سجل RecurringDay ومدة نوع الموعد بالدقائق.
    يأخذ في الاعتبار استراحة اختيارية (break_start/break_end).
    """
    slots = []
    slot_length = timedelta(minutes=duration_minutes)

    day_start = datetime.combine(day_date, recurring_day_obj.start_time)
    day_end = datetime.combine(day_date, recurring_day_obj.end_time)

    # فترات الاستراحة
    break_start_dt = None
    break_end_dt = None
    if recurring_day_obj.break_start and recurring_day_obj.break_end:
        break_start_dt = datetime.combine(day_date, recurring_day_obj.break_start)
        break_end_dt = datetime.combine(day_date, recurring_day_obj.break_end)
        # إذا كانت بيانات الاستراحة غير صالحة (break_start >= break_end)، نتجاهلها
        if break_start_dt >= break_end_dt:
            break_start_dt = None
            break_end_dt = None

    current_start = day_start
    while current_start + slot_length <= day_end:
        # التحقق مما إذا كان الوقت يقع ضمن فترة الاستراحة
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
    يبحث في الأيام القادمة look_ahead_days عن الفترات الزمنية الحرة لـ
    نوع الموعد المحدد. يأخذ في الاعتبار:
    - RecurringDay (مع day_of_week، start_date، end_date)
    - ExcludedDay
    - المواعيد المحجوزة بالفعل
    - يتم تخطي عطلة نهاية الأسبوع (السبت/الأحد)
    """
    type_obj = AppointmentType.query.get(appointment_type_id)
    if not type_obj:
        return []

    today = date.today()
    end_date = today + timedelta(days=look_ahead_days)
    free_slots = []

    # تحميل جميع سجلات RecurringDay
    recurring_days = RecurringDay.query.all()

    # جمع الأيام المستثناة الفردية
    excluded = {excl.date for excl in ExcludedDay.query.all()}

    # المواعيد المحجوزة في الفترة
    booked_appointments = Appointment.query.filter(
        Appointment.date >= today,
        Appointment.date <= end_date
    ).all()

    # booked_map[التاريخ] = [(start_dt, end_dt), ...]
    booked_map = {}
    for appt in booked_appointments:
        appt_start = datetime.combine(appt.date, appt.time)
        appt_end = appt_start + timedelta(minutes=appt.type.duration)
        booked_map.setdefault(appt.date, []).append((appt_start, appt_end))

    # لكل يوم من اليوم حتى end_date
    for single_day in (today + timedelta(n) for n in range((end_date - today).days + 1)):
        dow = single_day.weekday()  # 0=الإثنين، 6=الأحد

        # يوم مستثنى أو عطلة نهاية الأسبوع؟
        if single_day in excluded:
            continue
        if dow > 4:  # السبت(5) أو الأحد(6)
            continue

        # البحث في جميع قواعد RecurringDay التي:
        # 1. لها نفس يوم الأسبوع
        # 2. single_day >= start_date و single_day <= end_date

        day_matches = [
            r for r in recurring_days
            if r.day_of_week == dow
            and r.start_date <= single_day <= r.end_date
        ]
        if not day_matches:
            continue

        # لكل قاعدة مطابقة، ننشئ الفترات الزمنية ونقوم بفلترة المحجوزة
        for rec in day_matches:
            daily_slots = generate_slots_for_day(single_day, rec, type_obj.duration)

            valid_slots = []
            for slot_start_dt in daily_slots:
                slot_end_dt = slot_start_dt + timedelta(minutes=type_obj.duration)
                # التحقق من التعارض مع المواعيد المحجوزة
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
# إعداد قاعدة البيانات المبدئي
# --------------------------------------
with app.app_context():
    db.create_all()
    # مثال: إضافة أنواع المواعيد القياسية، إذا لم تكن موجودة
    if AppointmentType.query.count() == 0:
        standard_types = [
            {'name': 'طلب جواز السفر', 'duration': 30},
            {'name': 'تصديق الأوراق', 'duration': 20}
        ]
        for st in standard_types:
            db.session.add(AppointmentType(name=st['name'], duration=st['duration']))
        db.session.commit()

# -----------------------------------
# المسارات
# -----------------------------------

@app.route('/')
def index():
    return render_template('index.html')

# الخطوة 1: اختيار نوع الموعد
@app.route('/book', methods=['GET', 'POST'])
def book_select_type():
    form = BookTypeForm()
    form.appointment_type.choices = [
        (t.id, t.name) for t in AppointmentType.query.order_by(AppointmentType.name.asc()).all()
    ]
    if form.validate_on_submit():
        return redirect(url_for('book_select_slot', type_id=form.appointment_type.data))
    return render_template('book_type.html', form=form)

# الخطوة 2: اختيار الفترة الزمنية الحرة + بيانات الاتصال
@app.route('/book/slot', methods=['GET', 'POST'])
def book_select_slot():
    type_id = request.args.get('type_id')
    if not type_id:
        flash('يرجى اختيار نوع الموعد أولاً.', 'warning')
        return redirect(url_for('book_select_type'))

    free_slots = get_free_slots_for_type(type_id)
    if not free_slots:
        flash('لا توجد فترات متاحة حاليًا لهذا النوع من المواعيد.', 'warning')
        return redirect(url_for('book_select_type'))

    form = BookSlotForm()
    form.timeslot.choices = [(slot, slot) for slot in free_slots]

    if form.validate_on_submit():
        slot_str = form.timeslot.data
        try:
            slot_dt = datetime.strptime(slot_str, '%Y-%m-%d %H:%M')
        except ValueError:
            flash('فترة الموعد المحددة غير صالحة.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

        # 1) حفظ الموعد
        last_appointment = Appointment.query.order_by(Appointment.appointment_number.desc()).first()
        next_number = last_appointment.appointment_number + 1 if last_appointment else 1

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
        except:
            db.session.rollback()
            flash('خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى.', 'danger')
            return redirect(url_for('book_select_slot', type_id=type_id))

        # 2) إرسال بريد إلكتروني للمستخدم
        # --------------------------------
        msg = Message(
            subject="تأكيد الموعد",
            recipients=[new_appointment.customer_email]
        )

        # محتوى البريد الإلكتروني
        msg.body = f"""
مرحبا {new_appointment.customer_name},

لقد قمت بحجز موعد!

رقم الموعد: {new_appointment.appointment_number}
التاريخ: {new_appointment.date.strftime('%Y-%m-%d')}
الوقت: {new_appointment.time.strftime('%H:%M')}

شكرًا لك!
فريق السفارة
"""

        # إذا كنت ترغب في إرسال رسائل بريد إلكتروني بصيغة HTML، يمكنك استخدام msg.html
        # msg.html = render_template('email_template.html', appointment=new_appointment)

        # إرسال البريد الإلكتروني فعليًا
        mail.send(msg)

        # 3) تقديم ملاحظات للمستخدم في تطبيق الويب (Flash / إعادة التوجيه)
        flash("تم حجز الموعد بنجاح! ستتلقى بريدًا إلكترونيًا للتأكيد قريبًا.", "success")
        return render_template(
            'booking_success.html',
            appointment=new_appointment,
            notification_message=""
        )

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
                flash('لم يتم العثور على موعد. يرجى التحقق من البيانات.', 'warning')
        except ValueError:
            flash('إدخال غير صالح. يرجى إدخال البيانات بشكل صحيح.', 'danger')

    return render_template('check_status.html', form=form)

# --- قسم الإدارة ---

# قسم الإدارة
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

@app.route('/admin/cleanup', methods=['POST'])
def cleanup_old_appointments():
    from datetime import date, timedelta
    threshold_date = date.today() - timedelta(days=2)
    
    old_appointments = Appointment.query.filter(Appointment.date < threshold_date).all()
    for old_appt in old_appointments:
        db.session.delete(old_appt)
    db.session.commit()

    flash(f"تم حذف المواعيد القديمة قبل {threshold_date}.", "info")
    return redirect(url_for('admin'))

# حذف الموعد
@app.route('/admin/delete/<int:appointment_id>', methods=['POST'])
def delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    flash(f'تم حذف الموعد رقم {appointment.appointment_number}.', 'info')
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

        # التحقق: start_time < end_time
        if start_t >= end_t:
            flash('يجب أن يكون وقت البدء قبل وقت الانتهاء.', 'danger')
            return redirect(url_for('add_recurring_day'))

        # التحقق: start_date <= end_date
        if start_d > end_d:
            flash('يجب أن يكون تاريخ البدء قبل (أو يساوي) تاريخ الانتهاء.', 'danger')
            return redirect(url_for('add_recurring_day'))

        # لكل يوم من أيام الأسبوع المختارة، يتم إنشاء سجل
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
            flash('تم إنشاء يوم/أيام الأسبوع المتكررة بنجاح.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('خطأ في قاعدة البيانات. قد يكون هناك تعارض.', 'danger')
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
            flash('تمت إضافة يوم الاستثناء.', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('هذا اليوم مستثنى بالفعل.', 'danger')
    return render_template('add_excluded_day.html', form=form)

@app.route('/admin/appointment_type/add', methods=['GET', 'POST'])
def add_appointment_type():
    form = AppointmentTypeForm()
    if form.validate_on_submit():
        existing = AppointmentType.query.filter_by(name=form.name.data).first()
        if existing:
            flash('هذا النوع من المواعيد موجود بالفعل.', 'warning')
            return redirect(url_for('admin'))

        new_type = AppointmentType(
            name=form.name.data,
            duration=form.duration.data,
            notification_message=form.notification_message.data
        )
        db.session.add(new_type)
        try:
            db.session.commit()
            flash(f'تمت إضافة نوع الموعد "{new_type.name}".', 'success')
            return redirect(url_for('admin'))
        except IntegrityError:
            db.session.rollback()
            flash('خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى.', 'danger')
    return render_template('add_appointment_type.html', form=form)

@app.route('/admin/reject/<int:appointment_id>', methods=['POST'])
def reject_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)
    if appt.status != 'مرفوض':
        appt.status = 'مرفوض'
        db.session.commit()
        flash(f'تم رفض الموعد {appt.appointment_number}.', 'info')
    else:
        flash('الموعد مرفوض بالفعل.', 'warning')
    return redirect(url_for('admin'))

@app.route('/admin/recurring_day/delete/<int:rd_id>', methods=['POST'])
def delete_recurring_day(rd_id):
    rd = RecurringDay.query.get_or_404(rd_id)
    db.session.delete(rd)
    db.session.commit()
    flash('تم حذف يوم الأسبوع المتكرر.', 'info')
    return redirect(url_for('admin'))

@app.route('/admin/excluded_day/delete/<int:ex_id>', methods=['POST'])
def delete_excluded_day(ex_id):
    ex = ExcludedDay.query.get_or_404(ex_id)
    db.session.delete(ex)
    db.session.commit()
    flash('تم حذف يوم الاستثناء.', 'info')
    return redirect(url_for('admin'))


@app.route('/delete_appointment_type/<int:t_id>', methods=['POST'])
def delete_appointment_type(t_id):
    """
    Löscht einen vorhandenen Termin-Typen aus der Datenbank.
    """
    # Versuche, den entsprechenden Termin-Typ zu finden
    appointment_type = AppointmentType.query.get_or_404(t_id)
    
    # Lösche den Termin-Typ aus der Datenbank
    db.session.delete(appointment_type)
    db.session.commit()
    
    # Ggf. Feedback an den User geben (falls du Flask-Flash verwendest)
    flash('Terminart wurde erfolgreich gelöscht.', 'success')
    
    # Leite zurück zum Admin-Dashboard oder woanders hin
    return redirect(url_for('admin'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=9000, debug=True)
