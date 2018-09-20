from flask import Flask, render_template, request, redirect, abort, flash, session
from flask_wtf.csrf import CSRFProtect
from mastodon import Mastodon
import sqlite3
from contextlib import closing
import string
import random
import configparser
from autofollow import autofollow

from Zodiac import Zodiac
from User import User

config = configparser.ConfigParser()
config.read('config.ini')
dbname = config['config']['dbname']
server_domain = config['config']['server_domain']
server_secret_key = config['config']['server_secret_key']
max_login = int(config['config']['max_login'])

client_name = 'atlas'
scopes = ['read:accounts', 'follow']

atlas_url = 'https:///'+server_domain+'atlas'
redirect_url = 'https://'+server_domain+'/atlas'

def create_app():
    app = Flask(__name__)
    app.secret_key = server_secret_key
    return app

app = create_app()
csrf = CSRFProtect(app)

def get_form_params():
    form = request.form
    if 'user_id' in form and 'domain' in form and 'uuid' in form:
        return request.form['user_id'], request.form['domain'], request.form['uuid']
    return '', '', ''

def save_uuid(user_id, domain, uuid):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('insert into uuid (uuid, user_id, domain, disable) values (?,?,?, 0)', (uuid, user_id, domain))
        conn.commit()

def load_from_uuid(uuid):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select user_id, domain secret from uuid where uuid=? and disable=0', (uuid,))
        fetch = c.fetchone()
        return fetch

def disable_uuid(uuid):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('update uuid set disable=1 where uuid=?', (uuid,))
        conn.commit()

def search_oauth_applications(domain):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select uid, secret from oauth_applications where domain=?', (domain,))
        fetch = c.fetchone()
        return fetch

def save_oauth_applications(domain, oauth_applications):
    uid = oauth_applications[0]
    secret = oauth_applications[1]
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('insert into oauth_applications (domain, uid, secret) values (?,?,?)', (domain, uid, secret))
        conn.commit()

def get_oauth_applications(domain):
    app_base_url = 'https://'+domain
    oauth_applications = search_oauth_applications(domain)
    if oauth_applications is None:
        try:
            oauth_applications = Mastodon.create_app(client_name, scopes=scopes, redirect_uris=redirect_url, api_base_url=app_base_url)
            save_oauth_applications(domain, oauth_applications)
        except:
            oauth_applications = ('', '')
    return oauth_applications

def get_redirect_params():
    form = request.form
    if 'uuid' in form and 'code' in form:
        return request.form['uuid'], request.form['code']
    return '', ''

def get_random_str(n=64):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(n)])

def login_count(zodiac_id):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select count(*) from user_zodiac where zodiac_id=?', (zodiac_id,))
        fetch = c.fetchone()
        return fetch[0]

@app.route('/atlas')
def index():
    code = request.args.get('code', default='')
    if code is not '':
        return load_uuid()

    zodiac_list = Zodiac.list()
    user_list = User.list()

    if 'session_id' not in session:
        uuid = get_random_str()
        return render_template('form.html', uuid=uuid, user_list=user_list, max_login=max_login, zodiac_list=zodiac_list)

    session_id = session['session_id']
    login_user = User.first(session_id=session_id)

    if login_user is None:
        uuid = get_random_str()
        return render_template('form.html', uuid=uuid, user_list=user_list, max_login=max_login, zodiac_list=zodiac_list)

    return render_template('room.html', login_user=login_user, user_list=user_list, max_login=max_login, zodiac_list=zodiac_list)

@app.route('/atlas/post', methods = ['POST'])
def post():
    user_id, domain, uuid = get_form_params()
    if user_id is '' or domain is '' or uuid is '':
        flash('情報の取得に失敗しました(user_id, domain, uuid)', 'error')
        return redirect(redirect_url, code=302)

    if 'session_id' in session:
        session_id = session['session_id']
        if User.first(session_id=session_id) is not None:
            flash('参加しています！', 'info')
            return redirect(redirect_url, code=302)

    save_uuid(user_id, domain, uuid)
    client_id, client_secret = get_oauth_applications(domain)
    if client_id is '' or client_secret is '':
        flash('情報の取得に失敗しました(cilent_id, client_secret)', 'error')
        return redirect(redirect_url, code=302)
    api_base_url = 'https://'+domain
    mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=api_base_url)
    auth_url = mastodon.auth_request_url(client_id=client_id, redirect_uris=redirect_url, scopes=scopes)
    return redirect(auth_url, code=302)

def load_uuid():
    return render_template('load_uuid.html')

@app.route('/atlas/get_auth', methods = ['POST'])
def get_auth():
    uuid, code = get_redirect_params()
    if uuid is '' or code is '':
        flash('情報の取得に失敗しました(uuid, code)', 'error')
        return redirect(redirect_url, code=302)
    info = load_from_uuid(uuid)
    if info is None:
        flash('情報の取得に失敗しました(info)', 'error')
        return redirect(redirect_url, code=302)
    disable_uuid(uuid)
    user_id, domain = info
    client_id, client_secret = get_oauth_applications(domain)
    api_base_url = 'https://'+domain
    mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=api_base_url)
    try:
        access_token = mastodon.log_in(code=code, scopes=scopes, redirect_uri=redirect_url)
    except:
        access_token = ''

    if access_token is '':
        flash('情報の取得に失敗しました(access_token)', 'error')
        return redirect(redirect_url, code=302)

    login_user = mastodon.account_verify_credentials()

    if User.first(access_token=access_token) is None:
        if User.first(user_id=user_id, domain=domain) is not None:
            flash('参加しています！', 'info')
        else:
            flash('参加しました！', 'info')
    else:
        flash('参加しています！', 'info')
    user = User.first(user_id=user_id, domain=domain)
    if user is not None:
        user.drop()
    session_id = get_random_str()
    user = User(None, access_token, user_id, domain, session_id, login_user.avatar)
    user.save()
    session['session_id'] = session_id

    return redirect(redirect_url, code=302)

@app.route('/atlas/logout', methods = ['POST'])
def logout():
    session_id = session.pop('session_id', None)
    if session_id is None:
        flash('情報の取得に失敗しました(session_id)', 'error')
        return redirect(redirect_url, code=302)
    user = User.first(session_id=session_id)
    user.drop()
    flash('退出しました！', 'info')
    return redirect(redirect_url, code=302)

@app.route('/atlas/entry', methods = ['POST'])
def entry():
    if 'zodiac_id' not in request.json:
        return ''
    zodiac_id = request.json['zodiac_id']
    if login_count(zodiac_id) >= max_login:
        flash('ログイン人数が上限に達しています', 'error')
        return redirect(redirect_url, code=302)

    if 'session_id' not in session:
        return ''
    session_id = session['session_id']
    user = User.first(session_id=session_id)
    user.add_zodiac(zodiac_id)
    api_base_url = "https://"+user.domain
    mastodon = Mastodon(access_token=user.access_token, api_base_url=api_base_url)

    autofollow(mastodon, user.user_id, user.domain, zodiac_id)

    zodiac = Zodiac.first(id=zodiac_id)
    return render_template('zodiac_list.html', login_user=user, zodiac=zodiac, max_login=max_login)

@app.route('/atlas/exit', methods = ['POST'])
def exit():
    if 'zodiac_id' not in request.json:
        return ''
    zodiac_id = request.json['zodiac_id']
    if 'session_id' not in session:
        return ''
    session_id = session['session_id']
    user = User.first(session_id=session_id)
    user.del_zodiac(zodiac_id)
    zodiac = Zodiac.first(id=zodiac_id)
    return render_template('zodiac_list.html', login_user=user, zodiac=zodiac, max_login=max_login)
