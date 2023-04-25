from datetime import datetime, date
from functools import wraps

from flask import Blueprint, render_template, flash, redirect, url_for, abort
from flask_login import current_user, login_required
from sqlalchemy import func, or_

from auth import signup_post
from database import db_session
from forms import AddInvestmentCycleForm, AddMemberForm, MakeInvestmentForm, AddLoanForm, LoanPaymentForm
from models import InvestmentCycle, Investment, Member, Loan, Payment, Role, User

main = Blueprint('main', __name__)


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.roles[0].name == 'admin':
            abort(403)  # Forbidden
        return func(*args, **kwargs)

    return decorated_view


def user_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.roles[0].name == 'admin' and \
                not current_user.roles[0].name == 'member':
            abort(403)  # Forbidden
        return func(*args, **kwargs)

    return decorated_view


@main.route('/home')
@login_required
@user_required
def home():
    # Get the current user's investment and borrowing data
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()
    if current_user.roles[0].name != 'admin':
        investments = db_session.query(func.sum(Investment.amount)).filter_by(member_id=current_user.id).scalar() or 0
        borrowings = db_session.query(func.sum(Loan.amount)).filter_by(member_id=current_user.id).scalar() or 0
        interest = db_session.query(func.sum(Investment.profit)).filter_by(member_id=current_user.id).scalar() or 0

        # Calculate other metrics
        total_invested = investments + interest
        total_earned = round(interest - borrowings, 2)

        investment = db_session.query(User.fullname, func.sum(Investment.amount)). \
            join(Investment, User.id == Investment.member_id). \
            filter(User.id == current_user.id). \
            group_by(User.id).first()

        loans = db_session.query(User.fullname, func.sum(Loan.amount)). \
            join(Loan, User.id == Loan.member_id). \
            filter(User.id == current_user.id). \
            group_by(User.id).first()

        return render_template('home.html', investments=investments, borrowings=borrowings,
                               interest=interest, total_invested=total_invested, total_earned=total_earned,
                               investment=investment, loans=loans, legend='Home')

    else:
        investments = db_session.query(func.sum(Investment.amount)).filter(
            Investment.cycle_id == active_cycle.cycle_number).scalar() or 0
        borrowings = db_session.query(func.sum(Loan.amount)).filter(
            Loan.cycle_id == active_cycle.cycle_number).scalar() or 0
        interest = db_session.query(func.sum(Investment.profit)).filter(
            Investment.cycle_id == active_cycle.cycle_number).scalar() or 0

        # Calculate other metrics
        total_invested = investments + interest
        total_earned = round(interest - borrowings, 2)

        investment = db_session.query(User.fullname, func.sum(Investment.amount)). \
            join(Investment, User.id == Investment.member_id). \
            group_by(User.id).all()
        loans = db_session.query(User.fullname, func.sum(Loan.amount)). \
            join(Loan, User.id == Loan.member_id). \
            group_by(User.id).all()

        # Render the dashboard template with the data
        return render_template('home.html', investments=investments, borrowings=borrowings,
                               interest=interest, total_invested=total_invested, total_earned=total_earned,
                               investment=investment, loans=loans, active_cycle=active_cycle)


@main.route('/investments', methods=['GET', 'POST'])
@login_required
@user_required
def investments():
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()

    if current_user.roles[0].name == 'admin':
        if active_cycle is None:
            flash('There are no active investment cycles at the moment.')
            return redirect(url_for('main.investment_cycles'))
        else:
            investments = Investment.query.filter(Investment.cycle_id == active_cycle.cycle_number).all()
            return render_template('investments.html', investments=investments)
    else:
        if active_cycle is None:
            flash('There are no active investment cycles at the moment.')
            return redirect(url_for('main.home'))
        investments = Investment.query.filter(Investment.cycle_id == active_cycle.cycle_number,
                                              Investment.member_id == current_user.id).all()
        return render_template('investments.html', investments=investments)



@main.route('/investment-cycles', methods=['GET', 'POST'])
@login_required
@admin_required
def investment_cycles():
    form = AddInvestmentCycleForm()
    if form.validate_on_submit():
        cycle_number = form.cycle_number.data
        start_date = form.start_date.data
        end_date = form.end_date.data
        interest_rate = form.interest_rate.data
        min_investment = form.min_investment.data
        max_investment = form.max_investment.data
        cycle = InvestmentCycle(cycle_number=cycle_number, start_date=start_date, end_date=end_date,
                                interest_rate=interest_rate, min_investment=min_investment,
                                max_investment=max_investment)
        db_session.add(cycle)
        db_session.commit()
        flash('Investment cycle added successfully!')
        return redirect(url_for('main.investment_cycles'))
    cycles = InvestmentCycle.query.all()
    return render_template('investment_cycles.html', form=form, cycles=cycles)


@main.route('/add-member', methods=['GET', 'POST'])
@login_required
@admin_required
def add_member():
    # return 'only admins can access this resource'
    form = AddMemberForm()
    if form.validate_on_submit():
        name = form.name.data
        phone_number = form.phone_number.data
        email = form.email.data
        role = Role.query.filter_by(id=form.role.data).first()
        signup_post(email, name, phone_number, role)
        member = Member(name=name, phone_number=phone_number, email=email)
        db_session.add(member)
        db_session.commit()
        flash('User Added Successfully!')
        return redirect(url_for('main.home'))
    return render_template('add_member.html', form=form)


@main.route('/add_cycle', methods=['GET', 'POST'])
@login_required
@admin_required
def add_cycle():
    form = AddInvestmentCycleForm()

    if form.validate_on_submit():

        # Define the new date range
        start_date = form.start_date.data
        end_date = form.end_date.data

        # Check if the new range falls within any existing ranges
        max_end_date = db_session.query(func.max(InvestmentCycle.end_date)).scalar()

        # check if the new range start date is greater than or equal to the maximum end date
        if max_end_date and datetime.combine(start_date, datetime.min.time()) < max_end_date:
            # The new range falls within an existing range
            flash("The date ranges falls within an already existing date")
            return redirect(url_for('main.investment_cycles'))
        else:
            if start_date <= date.today():
                active = True
            else:
                active = False

            # cycle_number = form.cycle_number.data
            interest_rate = form.interest_rate.data
            min_investment = form.min_investment.data
            max_investment = form.max_investment.data

            cycle = InvestmentCycle(start_date=start_date,
                                    end_date=end_date,
                                    interest_rate=interest_rate,
                                    min_investment=min_investment,
                                    max_investment=max_investment,
                                    active=active)

            db_session.add(cycle)
            db_session.commit()

            flash('Cycle added successfully!', 'success')
            return redirect(url_for('main.investment_cycles'))

    return render_template('add_cycle.html', form=form)


@main.route('/edit_cycle/<int:cycle_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_cycle(cycle_id):
    cycle = InvestmentCycle.query.filter(InvestmentCycle.cycle_number == cycle_id).first()
    form = AddInvestmentCycleForm(obj=cycle)
    if form.validate_on_submit():
        cycle.cycle_number = form.cycle_number.data
        cycle.start_date = form.start_date.data
        cycle.end_date = form.end_date.data
        cycle.interest_rate = form.interest_rate.data
        cycle.min_investment = form.min_investment.data
        cycle.max_investment = form.max_investment.data
        db_session.commit()
        flash('Cycle has been updated.', 'success')
        return redirect(url_for('main.investment_cycles'))
    return render_template('add_cycle.html', form=form, legend='Edit Cycle')


@main.route('/add_investment', methods=['GET', 'POST'])
@login_required
@user_required
def add_investment():
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()
    form = MakeInvestmentForm()
    if active_cycle is None:
        flash('There are no active investment cycles at the moment. Please add a new cycle.')
        return redirect(url_for('main.investment_cycles'))
    form.cycle_id.data = active_cycle.cycle_number
    form.interest_rate.data = active_cycle.interest_rate - 0.05
    form.start_date.data = datetime.utcnow()
    form.end_date.data = active_cycle.end_date

    if form.validate_on_submit():
        member_id = int(form.member_id.data)
        amount = form.amount.data
        interest = form.interest_rate.data
        cycle_id = form.cycle_id.data
        investment_date = form.start_date.data
        maturity_date = form.end_date.data
        profit = form.profit.data

        # Check if investment amount is within limits for the active cycle
        if amount < active_cycle.min_investment or amount > active_cycle.max_investment:
            flash(
                f'Investment amount should be between {active_cycle.min_investment} and {active_cycle.max_investment}')
            return redirect(url_for('main.add_investment'))

        investment = Investment(member_id=member_id, amount=amount, interest=interest,
                                cycle_id=cycle_id, profit=profit, investment_date=investment_date,
                                maturity_date=maturity_date)
        db_session.add(investment)
        db_session.commit()
        flash('Investment added successfully')
        return redirect(url_for('main.investments'))

    return render_template('add_investment.html', title='Add Investment', form=form, active_cycle=active_cycle)


@main.route('/add_loan', methods=['GET', 'POST'])
@login_required
@user_required
def add_loan():
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()
    if active_cycle is None:
        flash('There are no active investment cycles at the moment. Please add a new cycle.')
        return redirect(url_for('main.investment_cycles'))
    total_invest = db_session.query(func.sum(Investment.amount)).filter(
        Investment.cycle_id == active_cycle.cycle_number).scalar()
    total_loans = db_session.query(func.sum(Loan.amount)).filter(Loan.cycle_id == active_cycle.cycle_number).scalar()
    if total_loans is None:
        total_loans = 0
    if total_invest is None:
        total_invest = 0
    funds_avaliable = total_invest - total_loans
    interest_rate = active_cycle.interest_rate
    start_date = datetime.utcnow()
    max_date = active_cycle.end_date
    form = AddLoanForm()
    # form.member_id.choices = [(str(m.id), m.name) for m in Member.query.all()]
    form.member_id.choices = [(str(current_user.id), current_user.fullname)]
    form.start_date.data = start_date
    form.max_date.data = max_date
    form.interest_rate.data = interest_rate
    form.funds_avaliable.data = funds_avaliable
    if form.validate_on_submit():
        member_id = int(form.member_id.data)
        amount = form.amount.data
        interest_rate = float(form.interest_rate.data)
        start_date = form.start_date.data
        end_date = form.end_date.data
        payment_frequency = form.payment_frequency.data
        cycle_id = active_cycle.cycle_number

        loan = Loan(member_id=member_id, amount=amount, interest_rate=interest_rate,
                    start_date=start_date, end_date=end_date, payment_frequency=payment_frequency, cycle_id=cycle_id)
        db_session.add(loan)
        db_session.commit()

        flash('Loan added successfully!')
        return redirect(url_for('main.home', member_id=member_id))
    return render_template('add_loan.html', form=form)


###############################################################################
# Route to add payment for a loan

@main.route('/loan/<int:loan_id>/payment/add', methods=['GET', 'POST'])
@login_required
@user_required
def add_loan_payment(loan_id):
    # loan = Loan.query.get(loan_id)
    # if loan is None or loan.member.user != current_user:
    #    abort(404)

    form = LoanPaymentForm()
    if form.validate_on_submit():
        loan = Payment.query.filter(Payment.loan_id == loan_id)
        payment = Payment(payment_date=form.payment_date.data, amount=form.amount_paid.data, loan_id=loan_id)
        db_session.add(payment)
        db_session.commit()
        flash('Payment added successfully.', 'success')
        return redirect(url_for('main.view_loans'))

    return render_template('add_loan_payment.html', form=form)


# Route to edit payment for a loan
@main.route('/loan/payment/<int:payment_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_loan_payment(payment_id):
    payment = Payment.query.get(payment_id)
    # if payment is None or payment.loan.member.user != current_user:
    #    abort(404)

    form = LoanPaymentForm(obj=payment)
    if form.validate_on_submit():
        form.populate_obj(payment)
        db_session.commit()
        flash('Payment edited successfully.', 'success')
        return redirect(url_for('main.view_loan', loan_id=payment.loan.id))

    return render_template('edit_loan_payment.html', form=form, payment=payment)


# Route to delete payment for a loan
@main.route('/loan/payment/<int:payment_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_loan_payment(payment_id):
    return "Only Admins can access this resource"
    payment = Payment.query.get(payment_id)
    # if payment is None or payment.loan.member.user != current_user:
    #    abort(404)

    db_session.delete(payment)
    db_session.commit()
    flash('Payment deleted successfully.', 'success')
    return redirect(url_for('main.view_loan', loan_id=payment.loan.id))


# Route to view all loans
@main.route('/loans')
@login_required
@user_required
def view_loans():
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()
    if current_user.roles[0].name == 'member':

        loans = Loan.query.filter(Loan.member_id == current_user.id, or_(
            Loan.cycle_id == active_cycle.cycle_number,
            Loan.is_paid == False,
            Loan.is_overdue == True)).all()

        for loan in loans:
            loan.amountdue = amount_due(loan.amount, loan.start_date, loan.cycle_id)
            loan.penalty = calculate_penalty(loan.start_date, loan.id, loan.end_date)
            payments = Payment.query.filter_by(loan_id=loan.id).all()
            loan.total_paid = sum(payment.amount for payment in payments)
            loan.balance = round(loan.amountdue - loan.total_paid, 2)
            if loan.balance <= 0.0:
                loan.is_paid = True
                loan.is_overdue = False
                loan.end_date = datetime.utcnow()
            db_session.commit()

        return render_template('loans.html', loans=loans)
    else:
        loans = Loan.query.filter(or_(
            Loan.cycle_id == active_cycle.cycle_number,
            Loan.is_paid == False,
            Loan.is_overdue == True)).all()

        for loan in loans:
            loan.amountdue = amount_due(loan.amount, loan.start_date, loan.cycle_id)
            loan.penalty = calculate_penalty(loan.start_date, loan.id, loan.end_date)
            payments = Payment.query.filter_by(loan_id=loan.id).all()
            loan.total_paid = sum(payment.amount for payment in payments)
            loan.balance = round(loan.amountdue - loan.total_paid, 2)
            if loan.balance <= 0.0:
                loan.is_paid = True
                loan.is_overdue = False
                loan.end_date = datetime.utcnow()
            db_session.commit()

        return render_template('loans.html', loans=loans)



# Route to view details of a loan
@main.route('/loan/<int:loan_id>')
@login_required
@user_required
def view_loan(loan_id):
    loan = Loan.query.get(loan_id)
    payments = loan.payments
    form = LoanPaymentForm()
    return render_template('view_loan.html', form=form, loan=loan, payments=payments)


def cycle():
    active_cycle = InvestmentCycle.query.filter(InvestmentCycle.active == True).first()
    return active_cycle


def amount_due(amount, date_start, loanid):
    date = datetime.utcnow()

    cycle_start = cycle().start_date
    cycle_end = cycle().end_date

    if date > cycle_end:
        active_cycle = InvestmentCycle.querry.filter(InvestmentCycle.cycle_number == loanid)
        days_in_cycle = (active_cycle.end_date - active_cycle.start_date).days
        days_elapsed = (active_cycle.end_date - date_start).days
        interest_per_day = active_cycle.interest_rate / days_in_cycle

        days_elapsed = (date - active_cycle.end_date).days
        penalty_rate = 0.05  # 5% penalty rate per day
        penalty = round(amount * penalty_rate * days_elapsed, 2)
        amountDue = round(amount * interest_per_day * days_elapsed, 2) + amount + penalty

        return amountDue

    else:
        if date < cycle_start:
            return 0.0
        else:
            days_in_cycle = (cycle_end - cycle_start).days
            days_elapsed = (date - date_start).days
            interest_per_day = cycle().interest_rate / days_in_cycle
            amountDue = round(amount * interest_per_day * days_elapsed, 2) + amount
            return amountDue


def calculate_penalty(loandate, loan_id, amount):
    if cycle().end_date < loandate:
        active_cycle = InvestmentCycle.query.filter(InvestmentCycle.cycle_number)

        date = datetime.utcnow()
        # if date <= calculate_interest():

        days_elapsed = (date - active_cycle.end_date).days
        penalty_rate = 0.05  # 5% penalty rate per day
        penalty = round(amount * penalty_rate * days_elapsed, 2)
        return penalty
    else:
        return 0.0


def calculate_total_due(self, date=None):
    if not date:
        date = datetime.utcnow().date()

    interest = self.calculate_interest(date)
    penalty = self.calculate_penalty(date)

    return round(self.amount + interest + penalty, 2)
