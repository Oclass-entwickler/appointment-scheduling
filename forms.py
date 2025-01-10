from flask_wtf import FlaskForm
from wtforms import (
    StringField, SelectField, SelectMultipleField,
    TimeField, DateField, IntegerField, SubmitField, widgets, TextAreaField
)
from wtforms.validators import DataRequired, Email, NumberRange

class MultiCheckboxField(SelectMultipleField):
    """
    حقل اختيار متعدد (Checkbox) لأيام الأسبوع.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class BookTypeForm(FlaskForm):
    """
    الخطوة 1: اختيار نوع الموعد.
    """
    appointment_type = SelectField('نوع الموعد', coerce=int, validators=[DataRequired()])
    submit = SubmitField('التالي')

class BookSlotForm(FlaskForm):
    """
    الخطوة 2: اختيار وقت محدد وإدخال تفاصيل المستخدم.
    """
    timeslot = SelectField('الأوقات المتاحة', coerce=str, validators=[DataRequired()])
    customer_name = StringField('الاسم', validators=[DataRequired()])
    customer_email = StringField('البريد الإلكتروني', validators=[DataRequired(), Email()])
    birth_date = DateField('تاريخ الميلاد (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('حجز الموعد')

class StatusForm(FlaskForm):
    """
    التحقق من حالة الموعد.
    """
    customer_name = StringField('الاسم', validators=[DataRequired()])
    appointment_number = StringField('رقم الموعد', validators=[DataRequired()])
    birth_date = DateField('تاريخ الميلاد (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('التحقق من الحالة')

class RecurringDayForm(FlaskForm):
    """
    نموذج لإضافة أيام الأسبوع المتكررة مع التواريخ وأوقات العمل.
    """
    days_of_week = MultiCheckboxField(
        'أيام الأسبوع',
        choices=[
            ('0', 'الاثنين'),
            ('1', 'الثلاثاء'),
            ('2', 'الأربعاء'),
            ('3', 'الخميس'),
            ('4', 'الجمعة')
        ],
        validators=[DataRequired()]
    )
    start_date = DateField('تاريخ البداية (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('تاريخ النهاية (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    start_time = TimeField('وقت البداية (HH:MM)', format='%H:%M', validators=[DataRequired()])
    end_time = TimeField('وقت النهاية (HH:MM)', format='%H:%M', validators=[DataRequired()])
    break_start = TimeField('بداية الاستراحة (HH:MM)', format='%H:%M')
    break_end = TimeField('نهاية الاستراحة (HH:MM)', format='%H:%M')
    submit = SubmitField('حفظ')

class ExcludedDayForm(FlaskForm):
    """
    نموذج لإضافة يوم استثناء.
    """
    date = DateField('التاريخ (YYYY-MM-DD)', format='%Y-%m-%d', validators=[DataRequired()])
    reason = StringField('السبب (اختياري)')
    submit = SubmitField('إضافة يوم الاستثناء')

class AppointmentTypeForm(FlaskForm):
    """
    نموذج لإضافة نوع الموعد.
    """
    name = StringField('اسم نوع الموعد', validators=[DataRequired()])
    duration = IntegerField('المدة (بالدقائق)', validators=[DataRequired(), NumberRange(min=1)])
    notification_message = TextAreaField('رسالة الإشعار (اختياري)')
    submit = SubmitField('إضافة نوع الموعد')
