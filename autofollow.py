from mastodon import Mastodon
import sqlite3
from contextlib import closing
import configparser

from Zodiac import Zodiac

config = configparser.ConfigParser()
config.read('config.ini')
dbname = config['config']['dbname']
server_domain = config['config']['server_domain']
server_secret_key = config['config']['server_secret_key']

def get_member(zodiac_id):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select access_token, user.user_id, domain from user left join user_zodiac on user.id=user_zodiac.user_id where user_zodiac.zodiac_id=?', (zodiac_id,))
        fetch = c.fetchall()
        return fetch

def autofollow(mastodon, user_id, domain, zodiac_id):
    member = get_member(zodiac_id)

    for user in member:
        a_tk, u_id, dmin = user
        if user_id == u_id and domain == dmin:
            continue
        api_base_url = 'https://'+dmin
        mstdn = Mastodon(access_token=a_tk, api_base_url=api_base_url)
        uri = u_id+'@'+dmin
        mastodon.follows(uri)
        uri = user_id+'@'+domain
        mstdn.follows(uri)

    zodiac = Zodiac.first(id=zodiac_id)
    if zodiac.uri is '' or zodiac.uri is None:
        return
    mastodon.follows(zodiac.uri)
