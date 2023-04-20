import secrets
from datetime import datetime

# Database Models
import bcrypt
from flask import current_app
from flask_login import UserMixin
from flask_security import RoleMixin
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Float, Boolean, event, func, Table
from sqlalchemy.orm import relationship

from database import Base, db_session


class Role(Base, RoleMixin):
    __tablename__ = 'roles'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'<Role {self.name}>'


user_roles = Table('user_roles',
                   Base.metadata,
                   Column('user_id', Integer(), ForeignKey('users.id')),
                   Column('role_id', Integer(), ForeignKey('roles.id'))
                   )


class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True)
    fullname = Column(String(255), default=None)
    phone_number = Column(String(255), default=None)
    password = Column(String(255))
    active = Column(Boolean(), default=False)
    activation_token = Column(String(255), unique=True)
    roles = relationship('Role', secondary=user_roles, backref='users')
    loans = relationship('Loan', backref='users', lazy=True)
    investments = relationship('Investment', backref='users', lazy=True)

    def __init__(self, email, password, phone_number, fullname, active):
        self.email = email
        self.fullname = fullname
        self.password = password
        self.phone_number = phone_number
        self.activation_token = secrets.token_urlsafe()
        self.active = active

    def __repr__(self):
        return f'<User {self.email}>'

    def get_email_confirmation_token(self):
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        # salt = bcrypt.gensalt().decode('utf-8')
        data = {'email': self.email, 'active': self.active}
        return serializer.dumps(data)



def decode_confirmation_token(token):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    # salt = bcrypt.gensalt().decode('utf-8')
    data = serializer.loads(token)
    email = data['email']
    active = data['active']
    return email, active


class Member(Base):
    __tablename__ = 'member'
    id = Column(Integer, primary_key=True)
    name = Column(String(50), nullable=False)
    phone_number = Column(String(20), nullable=False)
    email = Column(String(120), nullable=False, unique=True)
    join_date = Column(DateTime, default=datetime.utcnow)
    # loans = relationship('Loan', backref='member', lazy=True)
    # investments = relationship('Investment', backref='member', lazy=True)

    def __repr__(self):
        return f'<Member {self.name}>'


class Loan(Base):
    __tablename__ = 'loan'
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    interest_rate = Column(Float, nullable=False)
    payment_frequency = Column(Integer, nullable=False)
    payments = relationship('Payment', backref='loan', lazy=True)
    balance = Column(Float, default=0.0, nullable=False)
    amountdue = Column(Float, default=0.0, nullable=False)
    total_paid = Column(Float, default=0.0, nullable=False)
    penalties = relationship('Penalty', backref='loan', lazy=True)
    cycle_id = Column(Integer, ForeignKey('investment_cycle.cycle_number'), nullable=False)
    is_paid = Column(Boolean, default=False)
    is_overdue = Column(Boolean, default=False)

    def __repr__(self):
        return f'<Loan {self.id}>'

    def calculate_interest(self, date=None):
        if not date:
            date = datetime.utcnow().date()

        cycle_start = self.cycle.start_date
        cycle_end = self.cycle.end_date

        if date > cycle_end:
            date = cycle_end

        if date < cycle_start:
            return 0.0

        days_in_cycle = (cycle_end - cycle_start).days
        days_elapsed = (date - cycle_start).days

        interest_per_day = self.interest_rate / days_in_cycle
        interest = round(self.balance * interest_per_day * days_elapsed, 2)

        return interest

    def calculate_penalty(self, date=None):
        if not date:
            date = datetime.utcnow().date()

        if date <= self.end_date:
            return 0.0

        days_elapsed = (date - self.end_date).days
        penalty_rate = 0.05  # 5% penalty rate per day
        penalty = round(self.amount * penalty_rate * days_elapsed, 2)

        return penalty

    def calculate_total_due(self, date=None):
        if not date:
            date = datetime.utcnow().date()

        interest = self.calculate_interest(date)
        penalty = self.calculate_penalty(date)

        return round(self.amount + interest + penalty, 2)


class Investment(Base):
    __tablename__ = 'investment'
    id = Column(Integer, primary_key=True)
    member_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    amount = Column(Float, nullable=False)
    investment_date = Column(DateTime, default=datetime.utcnow)
    maturity_date = Column(DateTime, nullable=False)
    interest = Column(Float, nullable=True)
    cycle_id = Column(Integer, ForeignKey('investment_cycle.id'), nullable=False)
    profit = Column(Float, nullable=False)

    def __repr__(self):
        return f'<Investment {self.amount, self.profit}>'


class Penalty(Base):
    __tablename__ = 'penalty'
    id = Column(Integer, primary_key=True)
    amount = Column(Float, nullable=False)
    date = Column(DateTime, nullable=False)
    investment_id = Column(Integer, ForeignKey('investment.id'), nullable=True)
    loan_id = Column(Integer, ForeignKey('loan.id'), nullable=True)

    def __repr__(self):
        return f'<Penalty {self.amount}>'


class Payment(Base):
    __tablename__ = 'payment'
    id = Column(Integer, primary_key=True)
    loan_id = Column(Integer, ForeignKey('loan.id'), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    amount = Column(Float, nullable=False)

    def __repr__(self):
        return f'<Payment {self.loan_id}>'


class InvestmentCycle(Base):
    __tablename__ = 'investment_cycle'
    id = Column(Integer, primary_key=True)
    cycle_number = Column(Integer, unique=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    interest_rate = Column(Float, nullable=False)
    min_investment = Column(Float, nullable=False)
    max_investment = Column(Float, nullable=False)
    investments = relationship('Investment', backref='cycle', lazy=True)
    loans = relationship('Loan', backref='cycle', lazy=True)
    active = Column(Boolean)

    def __repr__(self):
        return f'<InvestmentCycle {self.cycle_number}>'


@event.listens_for(InvestmentCycle, 'before_insert')
def generate_cycle_number(mapper, connection, target):
    max_cycle_number = db_session.query(func.max(InvestmentCycle.cycle_number)).scalar()

    if max_cycle_number is None:
        target.cycle_number = 1
    else:
        target.cycle_number = max_cycle_number + 1


# Define roles
roles = ['admin', 'member']
for role in roles:
    if not Role.query.filter_by(name=role).first():
        db_session.add(Role(name=role))
db_session.commit()
