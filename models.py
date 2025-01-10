from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time

db = SQLAlchemy()

class AppointmentType(db.Model):
    """
    تمثّل نوع الموعد، مثل "تقديم طلب جواز السفر".
    """
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)  # اسم نوع الموعد
    duration = db.Column(db.Integer, nullable=False)               # المدة بالدقائق
    notification_message = db.Column(db.Text, nullable=True)       # رسالة الإشعار لنوع الموعد

    def __repr__(self):
        return f"<AppointmentType {self.name}>"


class RecurringDay(db.Model):
    """
    يوم متكرر (مثل الاثنين - الجمعة) مع:
    - day_of_week: يوم الأسبوع (0=الاثنين، ...، 4=الجمعة)
    - صالح من start_date إلى end_date
    - وقت البداية والنهاية
    - فترة استراحة اختيارية (break_start, break_end)
    """
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=الاثنين، 1=الثلاثاء، ...، 4=الجمعة
    start_date = db.Column(db.Date, nullable=False)      # تاريخ البداية
    end_date = db.Column(db.Date, nullable=False)        # تاريخ النهاية
    start_time = db.Column(db.Time, nullable=False)      # وقت البداية
    end_time = db.Column(db.Time, nullable=False)        # وقت النهاية
    break_start = db.Column(db.Time, nullable=True)      # بداية الاستراحة
    break_end = db.Column(db.Time, nullable=True)        # نهاية الاستراحة

    def __repr__(self):
        return (f"<RecurringDay يوم={self.day_of_week}, "
                f"{self.start_date} - {self.end_date}>")


class ExcludedDay(db.Model):
    """
    يوم استثناء فردي (مثل العطلات الرسمية أو أيام الإغلاق).
    """
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)  # تاريخ الاستثناء
    reason = db.Column(db.String(200), nullable=True)       # السبب (اختياري)

    def __repr__(self):
        return f"<ExcludedDay {self.date} - {self.reason}>"


class Appointment(db.Model):
    """
    تمثّل موعدًا محجوزًا مع رقم فريد، وبيانات العميل، وتاريخ/وقت الموعد.
    """
    id = db.Column(db.Integer, primary_key=True)
    appointment_number = db.Column(db.Integer, unique=True, nullable=False)  # رقم الموعد
    type_id = db.Column(db.Integer, db.ForeignKey('appointment_type.id'), nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)               # اسم العميل
    customer_email = db.Column(db.String(100), nullable=False)              # البريد الإلكتروني
    birth_date = db.Column(db.Date, nullable=False)                         # تاريخ الميلاد
    date = db.Column(db.Date, nullable=False)                               # تاريخ الموعد
    time = db.Column(db.Time, nullable=False)                               # وقت الموعد
    status = db.Column(db.String(20), default='مسجل')                       # الحالة: مسجل/مرفوض

    type = db.relationship('AppointmentType', backref=db.backref('appointments', lazy=True))

    def __repr__(self):
        return f"<Appointment {self.appointment_number} - {self.customer_name}>"
