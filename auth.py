import hashlib
import secrets
import string
from flask import Blueprint, render_template, redirect, url_for, request, flash, g, session
from flask_login import login_user, logout_user
from flask_security import LoginForm, login_required, current_user, utils
from flask_mail import Message
from database import db_session
from forms import LoginForm, SetPasswordForm
from mail import mail
from models import User, decode_confirmation_token
from security import user_datastore

auth = Blueprint('auth', __name__)


@auth.route('/', methods=['GET', 'POST'])
def index():
    form = LoginForm()
    if form.validate_on_submit():
        # login code
        email = form.email.data
        password = form.password.data
        remember = form.remember.data

        user = user_datastore.get_user(email)

        if user is None:
            flash('Email address does not exists in the database. Contact your Administrator')
        if hashlib.sha256(password.encode()).hexdigest() != user.password:
            flash('Wrong Password, Please try again')
        else:
            # if the above check passes, then we know the user has the right credentials
            login_user(user, remember=remember)
            return redirect(url_for('main.home'))

    return render_template('index.html', form=form)


def signup_post(email, fullname, phone_number, role):
    email = email
    fullname = fullname
    phone_number = phone_number
    alphabet = string.ascii_letters + string.digits
    password = ''.join(secrets.choice(alphabet) for i in range(8))
    token = secrets.token_urlsafe()
    active = False
    roles = role

    user = user_datastore.get_user(email)
    if user is None:
        user = User(email=email, fullname=fullname, phone_number=phone_number,
                    password=hashlib.sha256(password.encode()).hexdigest(), active=active)

        user.roles.append(roles)
        db_session.add(user)
        #user_datastore.add_role_to_user(user, roles=roles)
        #user_datastore.create_user(user)
        db_session.commit()

        # Send activation email
        send_activation_email(user)

        return 'An activation email has been sent to your email address. Please check your email and follow the ' \
               'instructions to activate your account. '

    return 'An account already exists with that email address. Please log in or use a different email address.', 'warning'


def send_activation_email(user):
    token = user.get_email_confirmation_token()
    activation_link = url_for('auth.activate', token=token, _external=True)
    subject = 'Activate your account'
    sender = 'villagevault@mlinkme.click'
    body = f'Hello {user.email},\n\nThank you for registering for our app! To activate your account, please click on the following link:\n\n{activation_link}\n\nIf you did not register for our app, please ignore this email.\n\nBest regards,\nThe App Team'
    message = Message(subject=subject, body=body, recipients=[user.email], sender=sender)
    mail.send(message)


@auth.route('/activate/<token>', methods=['GET', 'POST'])
def activate(token):
    form = SetPasswordForm()
    if current_user.is_authenticated:
        return redirect(url_for('auth.home'))

    email, active = decode_confirmation_token(token)
    user = user_datastore.get_user(email)
    #user = User.query.filter_by(email=email).first()

    if email is None or active is None:
        flash('The activation link is invalid or has expired. Please request a new one.', 'danger')
        return redirect(url_for('auth.index'))

    if user.active:
        flash('Your account is already activated. Please log in.', 'info')
        return redirect(url_for('auth.index'))

    if request.method == 'POST':

        password = form.password.data
        if not user:
            flash('Unable to find user with email {}'.format(email), 'danger')
            return redirect(url_for('auth.index'))

        try:
            user.password = hashlib.sha256(password.encode()).hexdigest()
            user.active = True
            db_session.add(user)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            flash('Error updating user: {}'.format(str(e)), 'danger')
            return redirect(url_for('auth.index'))
        else:
            flash('Your account has been activated. Please log in.', 'success')
            return redirect(url_for('auth.index'))
    else:
        return render_template('activate.html', token=token, form=form, email=email)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.index'))
