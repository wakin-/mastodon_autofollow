from mastodon import Mastodon
import sqlite3
from contextlib import closing
from config import config

from Zodiac import Zodiac

dbname = config('dbname')
server_domain = config('server_domain')
server_secret_key = config('server_secret_key')

def get_member(zodiac_id):
    with closing(sqlite3.connect(dbname)) as conn:
        c = conn.cursor()
        c.execute('select access_token, user.user_id, domain from user left join user_zodiac on user.id=user_zodiac.user_id where user_zodiac.zodiac_id=?', (zodiac_id,))
        fetch = c.fetchall()
        return fetch

def autofollow(mastodon, user_id, domain, zodiac):
    member = get_member(zodiac.id)

    for user in member:
        a_tk, u_id, dmin = user
        if user_id == u_id and domain == dmin:
            continue
        api_base_url = 'https://'+dmin
        mstdn = Mastodon(access_token=a_tk, api_base_url=api_base_url)
        uri = u_id+'@'+dmin
        try:
            mastodon.follows(uri)
        except:
            pass
        uri = user_id+'@'+domain
        try:
            mstdn.follows(uri)
        except:
            pass

    if zodiac.uri is '' or zodiac.uri is None:
        return
    try:
        mastodon.follows(zodiac.uri)
    except:
        pass
