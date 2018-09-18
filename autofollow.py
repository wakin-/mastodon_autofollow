from mastodon import Mastodon
import sqlite3
from contextlib import closing
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
dbname = config['config']['dbname']
server_domain = config['config']['server_domain']
server_secret_key = config['config']['server_secret_key']

def get_member():
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select access_token, user_id, domain from access_token')
        fetch = c.fetchall()
        return fetch

def autofollow(mastodon, user_id, domain):
    member = get_member()

    for user in member:
        a_tk, u_id, dmin = user
        api_base_url = 'https://'+dmin
        mstdn = Mastodon(access_token=a_tk, api_base_url=api_base_url)
        uri = u_id+'@'+dmin
        mastodon.follows(uri)
        uri = user_id+'@'+domain
        mstdn.follows(uri)
