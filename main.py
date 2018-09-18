from flask import Flask, render_template, request, redirect, abort, flash, session
from mastodon import Mastodon
import sqlite3
from contextlib import closing
import string
import random
import configparser
from autofollow import autofollow

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

def check_access_token(access_token=None, user_id=None, domain=None, session_id=None):
    sql = 'select access_token, user_id, domain, session_id, avatar from access_token'
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        if access_token is not None:
            c.execute(sql+' where access_token=?', (access_token,))
        elif user_id is not None and domain is not None:
            c.execute(sql+' where user_id=? and domain=?', (user_id, domain))
        elif session_id is not None:
            c.execute(sql+' where session_id=?', (session_id,))
        else:
            c.execute(sql+' where 1=0')
        fetch = c.fetchone()
        return fetch

def save_access_token(access_token, user_id ,domain, session_id, avatar):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('insert into access_token (access_token, user_id, domain, session_id, avatar) values (?,?,?,?,?)', (access_token, user_id, domain, session_id, avatar))
        conn.commit()

def delete_access_token(access_token=None, session_id=None, user_id=None, domain=None):
    sql = 'delete from access_token where'
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        if access_token is not None:
            c.execute(sql+' access_token=?', (access_token,))
        elif user_id is not None and domain is not None:
            c.execute(sql+' user_id=? and domain=?', (user_id,domain))
        elif session_id is not None:
            c.execute(sql+' session_id=?', (session_id,))
        conn.commit()

def get_random_str(n=64):
    return ''.join([random.choice(string.ascii_letters + string.digits) for i in range(n)])

def get_login_user(session_id=None, access_token=None, domain=None):
    if session_id is not None:
        login_info = check_access_token(session_id=session_id)
        if login_info is None:
            return None
        access_token, user_id, domain, session_id, avatar = login_info

    api_base_url = 'https://'+domain
    mastodon = Mastodon(access_token=access_token, api_base_url=api_base_url)
    try:
        login_user = mastodon.account_verify_credentials()
        login_user.domain = domain
    except:
        session.pop('session_id', None)
        login_user = None
    return login_user

def login_count():
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select count(*) from access_token')
        fetch = c.fetchone()
        return fetch[0]

def get_login_users():
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select avatar from access_token')
        fetch = c.fetchall()
        return fetch

@app.route('/atlas')
def index():
    code = request.args.get('code', default='')
    if code is not '':
        return load_uuid()
    uuid = get_random_str()

    login_user = None
    if 'session_id' in session:
        session_id = session['session_id']
        login_user = get_login_user(session_id=session_id)

    count = login_count()

    login_users = get_login_users()

    return render_template('form.html', uuid=uuid, login_user=login_user, login_users=login_users, max_login=max_login)

@app.route('/atlas/post', methods = ['POST'])
def post():
    user_id, domain, uuid = get_form_params()
    if user_id is '' or domain is '' or uuid is '':
        flash('情報の取得に失敗しました(user_id, domain, uuid)', 'error')
        return redirect(redirect_url, code=302)

    if 'session_id' in session:
        session_id = session['session_id']
        if check_access_token(session_id=session_id) is not None:
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
    if login_count() >= max_login:
        flash('ログイン人数が上限に達しています', 'error')
        return redirect(redirect_url, code=302)

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

    if check_access_token(access_token=access_token) is None:
        if check_access_token(user_id=user_id, domain=domain) is not None:
            flash('参加しています！', 'info')
        else:
            autofollow(mastodon, user_id, domain)
            flash('参加しました！', 'info')
    else:
        flash('参加しています！', 'info')
    delete_access_token(user_id=user_id, domain=domain)
    session_id = get_random_str()
    save_access_token(access_token, user_id, domain, session_id, login_user.avatar)
    session['session_id'] = session_id

    return redirect(redirect_url, code=302)

@app.route('/atlas/logout', methods = ['POST'])
def logout():
    session_id = session.pop('session_id', None)
    if session_id is None:
        flash('情報の取得に失敗しました(session_id)', 'error')
        return redirect(redirect_url, code=302)
    delete_access_token(session_id=session_id)
    flash('退出しました！', 'info')
    return redirect(redirect_url, code=302)
