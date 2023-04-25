from datetime import datetime

from flask_login import current_user
from flask_wtf import FlaskForm
from sqlalchemy import Boolean
from werkzeug.routing import ValidationError
from wtforms import IntegerField, SelectField, SubmitField, DateField, DecimalField, StringField, BooleanField, \
    PasswordField, form
from wtforms.validators import DataRequired, NumberRange, Email, InputRequired, EqualTo
from models import Member, InvestmentCycle, Role, User
from security import user_datastore


class UniqueEmail(object):
    def __init__(self, message=None):
        if not message:
            message = 'Email Address already Registered'
        self.message = message

    def __call__(self, form, field):
        email = field.data
        member = Member.query.filter_by(email=email).first()
        try:
            if member:
                raise ValidationError(self.message)
        except ValidationError as e:
            field.errors.append(e.args[0])


class MakeInvestmentForm(FlaskForm):
    member_id = SelectField('Member ID', validators=[DataRequired()])
    amount = DecimalField('Amount', validators=[DataRequired(), NumberRange(min=0.01)])
    profit = DecimalField('Profit', validators=[DataRequired(), NumberRange(min=0.01)])
    cycle_id = StringField('Cycle ID', validators=[DataRequired()])
    interest_rate = DecimalField('Interest Rate', validators=[DataRequired(), NumberRange(min=0.0, max=1.0)])
    start_date = DateField('Investment Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('Investment Maturity Date', validators=[DataRequired()], format='%Y-%m-%d')
    submit = SubmitField('Make Investment')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        #self.member_id.choices = [(str(m.id), m.fullname) for m in user_datastore.get_user(current_user.id)]
        # Preload member_id field with current user's id and fullname
        self.member_id.choices = [(str(current_user.id), current_user.fullname)]

    def validate_member_id(self, field):
        if not User.query.filter_by(id=field.data).first():
            raise ValidationError('Invalid member ID')

    def validate_amount(self, field):
        member_id = int(self.member_id.data)
        if member_id and field.data < 0.01:
            raise ValidationError('Investment amount cannot be zero')


class AddInvestmentCycleForm(FlaskForm):
    cycle_number = IntegerField('Cycle Number', validators=[DataRequired(), NumberRange(min=1)])
    start_date = DateField('Start Date', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('End Date', validators=[DataRequired()], format='%Y-%m-%d')
    interest_rate = DecimalField('Interest Rate', validators=[DataRequired(), NumberRange(min=0.0, max=1.0)])
    min_investment = DecimalField('Minimum Investment', validators=[DataRequired(), NumberRange(min=0.01)])
    max_investment = DecimalField('Maximum Investment', validators=[DataRequired(), NumberRange(min=0.01)])
    active = BooleanField('Cycle Active', validators=None)
    submit = SubmitField('Add Cycle')


class AddMemberForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    phone_number = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email(), UniqueEmail()])
    role = SelectField('Role', choices=[(str(role.id), role.name) for role in Role.query.all()])
    submit = SubmitField('Add Member')


class AddLoanForm(FlaskForm):
    member_id = SelectField('Member ID', validators=[DataRequired()])
    amount = DecimalField('Loan Amount', validators=[DataRequired(), NumberRange(min=0)])
    amount_payable = DecimalField('Total Repayment', validators=[DataRequired(), NumberRange(min=0)])
    amount_install = DecimalField('Amount Per Installment', validators=[DataRequired(), NumberRange(min=0)])
    funds_avaliable = DecimalField('Maximum Loan Amount', validators=[DataRequired(), NumberRange(min=0)])
    start_date = DateField('Start Date', validators=[DataRequired()])
    end_date = DateField('End Date', validators=[DataRequired()])
    max_date = DateField('Maximum Repayment Date', validators=[DataRequired()])
    interest_rate = DecimalField('Interest Rate (%)', validators=[DataRequired(), NumberRange(min=0)])
    payment_frequency = IntegerField('Payment Frequency (in days)', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Add Loan')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # self.member_id.choices = [(str(m.id), m.name) for m in Member.query.all()]

    def validate_member_id(self, field):
        if not User.query.filter_by(id=field.data).first():
            raise ValidationError('Invalid member ID')

    def validate_amount(self, field):
        member_id = int(self.member_id.data)
        if member_id and field.data < 0.01:
            raise ValidationError('Loan amount cannot be zero')

    def validate_start_date(self, field):
        cycle = InvestmentCycle.query.filter(
            InvestmentCycle.start_date <= field.data,
            InvestmentCycle.end_date >= field.data
        ).first()
        if not cycle:
            raise ValidationError('Loan start date is outside of an active investment cycle')

    def validate_end_date(self, field):
        cycle = InvestmentCycle.query.filter(
            InvestmentCycle.start_date <= field.data,
            InvestmentCycle.end_date >= field.data
        ).first()
        if not cycle:
            raise ValidationError('Loan end date is outside of an active investment cycle')


class LoanPaymentForm(FlaskForm):
    amount_paid = DecimalField('Amount Paid', validators=[DataRequired(), NumberRange(min=0)])
    payment_date = DateField('Payment Date', validators=[DataRequired()])
    submit = SubmitField('Make Payment')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = StringField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class SetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password_verify = PasswordField('Verify Password', validators=[EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Submit')
