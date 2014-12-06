"""
=================
Home/Basic Stuff
=================
"""

from flask import Blueprint, session, request, render_template

from app.util import home_page
from app.util import generate_password_hash, check_password_hash, generate_deposit_address, is_logged_in, account_page, openorders
from app.database import db_session, redis
from app.models import *
from app.config import config
import time

home = Blueprint('home', __name__, url_prefix='/')


""" Basic/Account stuff """
@home.route('/')
def homepage():
    #for rule in app.url_map.iter_rules():
    #	if "GET" in rule.methods:
    #		print(rule.endpoint + " " + url_for(rule.endpoint))
    return home_page("ltc_btc")

@home.route('account')
def account():
    if not is_logged_in(session):
        return home_page("ltc_btc",danger="Please log in to perform that action.")
    return account_page()

@home.route('login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = User.query.filter(User.email==request.form['email']).first()
        if not user:
            return render_template('login2.html', error="Please check your email and username.")
        elif not check_password_hash(user.password, request.form['password']):
            return render_template('login2.html', error="Please check your email and username.")
        elif not user.activated:
            return render_template('login2.html', error="Please confirm your email before logging in.")
        else:
            session['logged_in'] = True
            session['userid'] = User.query.filter(User.email == request.form['email']).first().id
            session['expire'] = time.time() + 3600
            return home_page("ltc_btc",success="Logged in!")
    return render_template('login2.html')

@home.route('register',methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if "" in request.form.values():
            return render_template("register.html")
        if request.form['username'] in list(User.query.values(User.name)):
            return render_template("register.html",error="Please enter a password.")
        if request.form['email'] in list(User.query.values(User.email)):
            return render_template("register.html",error="Please enter a valid email.")
        if request.form['password'] != request.form['passwordconfirm']:
            return render_template("register.html",error="Passwords do not match.")
        #TODO: error for when they try to register when logged in already
        u = User(request.form['username'], request.form['email'],generate_password_hash(request.form['password'].strip()))
        db_session.add(u)
        db_session.commit()

        for currency in config.get_currencies():
            addr = generate_deposit_address(currency)
            a = Address(currency,addr,u.id)
            db_session.add(a)
        db_session.commit()
        if not send_confirm_email(u.id):
            return home_page("ltc_btc", danger='An error occured during registration. Please contact the administrator.')
        return home_page("ltc_btc", dismissable='Successfully registered. Please check your email and confirm your account before logging in.')

    if request.method == 'GET':
        return render_template("register.html")

@home.route("activate/<code>")
def activate_account(code):
    uid = redis.hget('activation_keys', code)
    if not uid:
        return  home_page("ltc_btc", danger='Invalid registration code!')
    user = User.query.filter(User.id==uid).first()
    if not user or user.activated:
        return  home_page("ltc_btc", danger='Account already registered or invalid code!')
    user.activated = True
    redis.hdel('activation_keys', code)
    db_session.commit()
    return home_page("ltc_btc", dismissable='Account successfully registered!')

@home.route('logout')
def logout():
    session.pop('logged_in', None)
    session.pop('userid', None)
    return home_page("ltc_btc", dismissable="Successfully logged out!")

def send_confirm_email(uid):
    user = User.query.filter(User.id==uid).first()
    if user:
        if not user.activated:
            code = generate_password_hash(str(random.random()))
            redis.hset("activation_keys", code, str(uid))
            msg = Message('Activation Code', sender="admin@gmail.org", recipients=[user.email])
            msg.body = "Thank you for signing up at OpenExchange. Activate your account at http://localhost:5000/activate/{}".format(code)
            mail.send(msg)
            return True
    return False

@home.route('trade/<instrument>')
def trade_page(instrument):
    if not config.is_valid_instrument(instrument):
        return home_page("ltc_btc", danger="Invalid trade pair!")
    return home_page(instrument)