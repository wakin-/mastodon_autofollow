from flask import Flask, render_template, request, redirect, abort, flash, session
from flask_wtf.csrf import CSRFProtect
from mastodon import Mastodon
import sqlite3
from contextlib import closing
import string
import random
from autofollow import autofollow
from announce import announce
from config import config

from Zodiac import Zodiac
from User import User

dbname = config('dbname')
server_domain = config('server_domain')
server_secret_key = config('server_secret_key')
max_login = int(config('max_login'))

client_name = 'atlas'
scopes = ['read:accounts', 'follow']

redirect_url = 'https://'+server_domain+'/atlas'

def create_app():
    app = Flask(__name__)
    app.secret_key = server_secret_key
    return app

app = create_app()
csrf = CSRFProtect(app)

def get_signin_params():
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

def get_login_user():
    if 'session_id' not in session:
        return None

    session_id = session['session_id']
    login_user = User.login_user(session_id)

    return login_user

def get_api_base_url(domain):
    return 'https://'+domain

@app.route('/atlas')
def index():
    code = request.args.get('code', default='')
    if code is not '':
        return load_uuid()

    zodiac_list = Zodiac.list()
    user_list = User.list()

    login_user = get_login_user()
    if login_user is None:
        uuid = get_random_str()
        return render_template('signin.html', uuid=uuid, user_list=user_list, max_login=max_login, zodiac_list=zodiac_list)

    return render_template('delete_signout.html', login_user=login_user, user_list=user_list, max_login=max_login, zodiac_list=zodiac_list)

@app.route('/atlas/signin', methods = ['POST'])
def signin():
    user_id, domain, uuid = get_signin_params()
    if user_id is '' or domain is '' or uuid is '':
        flash('情報の取得に失敗しました(user_id, domain, uuid)', 'error')
        return redirect(redirect_url, code=302)

    if get_login_user() is not None:
        flash('参加しています！', 'info')
        return redirect(redirect_url, code=302)

    save_uuid(user_id, domain, uuid)

    client_id, client_secret = get_oauth_applications(domain)
    if client_id is '' or client_secret is '':
        flash('情報の取得に失敗しました(cilent_id, client_secret)', 'error')
        return redirect(redirect_url, code=302)

    api_base_url = get_api_base_url(domain)
    mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=api_base_url)
    auth_url = mastodon.auth_request_url(client_id=client_id, redirect_uris=redirect_url, scopes=scopes)
    if auth_url is '':
        flash('情報の取得に失敗しました(auth_url)', 'error')
        return redirect(redirect_url, code=302)

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
    if client_id is '' or client_secret is '':
        flash('情報の取得に失敗しました(cilent_id, client_secret)', 'error')
        return redirect(redirect_url, code=302)

    api_base_url = get_api_base_url(domain)
    mastodon = Mastodon(client_id=client_id, client_secret=client_secret, api_base_url=api_base_url)
    try:
        access_token = mastodon.log_in(code=code, scopes=scopes, redirect_uri=redirect_url)
    except:
        flash('情報の取得に失敗しました(access_token)', 'error')
        return redirect(redirect_url, code=302)

    try:
        mastodon_account = mastodon.account_verify_credentials()
    except:
        flash('情報の取得に失敗しました(mastodon_account)', 'error')
        return redirect(redirect_url, code=302)

    session_id = get_random_str()
    session['session_id'] = session_id

    user = User.first(access_token=access_token)
    if user is None:
        user = User.first(user_id=user_id, domain=domain)
        if user is not None:
            user.access_token = access_token
            user.update()
            flash('Sign Inしています！', 'info')
        else:
            user = User(None, access_token, user_id, domain, mastodon_account.avatar)
            user.save()
            flash('Sign Inしました！', 'info')
    else:
        flash('Sign Inしています！', 'info')

    user.add_session(session_id)

    return redirect(redirect_url, code=302)

@app.route('/atlas/signout', methods = ['POST'])
def signout():
    login_user = get_login_user()
    session_id = session.pop('session_id', '')
    if login_user is not None:
        login_user.del_session(session_id)
    flash('Sign Outしました！', 'info')
    return redirect(redirect_url, code=302)

@app.route('/atlas/delete', methods = ['POST'])
def delete():
    login_user = get_login_user()
    if login_user is not None:
        login_user.drop()
    session_id = session.pop('session_id', '')
    flash('削除しました！', 'info')
    return redirect(redirect_url, code=302)

@app.route('/atlas/entry', methods = ['POST'])
def entry():
    if 'zodiac_id' not in request.json:
        return ''
    zodiac_id = request.json['zodiac_id']

    login_user = get_login_user()
    if login_user is None:
        return ''
    zodiac = Zodiac.first(id=zodiac_id)

    if login_count(zodiac_id) >= max_login:
        return render_template('zodiac_list.html', login_user=login_user, zodiac=zodiac, max_login=max_login, max=1)

    login_user.add_zodiac(zodiac_id)

    api_base_url = get_api_base_url(login_user.domain)
    mastodon = Mastodon(access_token=login_user.access_token, api_base_url=api_base_url)

    autofollow(mastodon, login_user.user_id, login_user.domain, zodiac)
    announce(login_user.user_id, login_user.domain, zodiac)

    return render_template('zodiac_list.html', login_user=login_user, zodiac=zodiac, max_login=max_login)

@app.route('/atlas/exit', methods = ['POST'])
def exit():
    if 'zodiac_id' not in request.json:
        return ''
    zodiac_id = request.json['zodiac_id']

    login_user = get_login_user()
    if login_user is None:
        return ''

    login_user.del_zodiac(zodiac_id)

    zodiac = Zodiac.first(id=zodiac_id)
    return render_template('zodiac_list.html', login_user=login_user, zodiac=zodiac, max_login=max_login)
