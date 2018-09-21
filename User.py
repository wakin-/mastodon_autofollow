import sqlite3
from contextlib import closing
from config import config

dbname = config('dbname')

class User:
    def __init__(self, id, access_token, user_id, domain, avatar):
        self.id = id
        self.access_token = access_token
        self.user_id = user_id
        self.domain = domain
        self.avatar = avatar

    def save(self):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('insert into user (access_token, user_id, domain, avatar) values (?,?,?,?)', (self.access_token, self.user_id, self.domain, self.avatar))
            conn.commit()

            c.execute('select id from user where access_token=?', (self.access_token,))
            fetch = c.fetchone()
            self.id = fetch[0] if fetch is not None else None

    def update(self):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('update user set access_token=?, user_id=?, domain=?, avatar=? where id=?', (self.access_token, self.user_id, self.domain, self.avatar, self.id))
            conn.commit()

    def drop(self):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('delete from user where id=?', (self.id,))
            c.execute('delete from user_zodiac where user_id=?', (self.id,))
            c.execute('delete from session where user_id=?', (self.id,))
            conn.commit()

    def add_session(self, session_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('insert into session (user_id, session_id) values (?,?)', (self.id, session_id))
            conn.commit()

    def del_session(self, session_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('delete from session where user_id=? and session_id=?', (self.id, session_id))
            conn.commit()

    def zodiac(self, zodiac_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('''select id, title
                         from zodiac left join user_zodiac on zodiac.id=user_zodiac.zodiac_id 
                         where user_zodiac.user_id=? and user_zodiac.zodiac_id=?''', (self.id, zodiac_id))
            fetch = c.fetchone()
            return fetch

    def zodiac_list(self):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('''select id, title
                         from zodiac left join user_zodiac on zodiac.id=user_zodiac.zodiac_id 
                         where user_zodiac.user_id=?''', (self.id,))
            fetch = c.fetchall()
            return fetch

    def add_zodiac(self, zodiac_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('insert into user_zodiac (user_id, zodiac_id) values (?,?)', (self.id, zodiac_id))
            conn.commit()

    def del_zodiac(self, zodiac_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('delete from user_zodiac where user_id=? and zodiac_id=?', (self.id, zodiac_id))
            conn.commit()

    @staticmethod
    def login_user(session_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('select user.id, access_token, user.user_id, domain, avatar from user left join session on user.id=session.user_id where session.session_id=?', (session_id,))
            fetch = c.fetchone()
            user = User(fetch[0], fetch[1], fetch[2], fetch[3], fetch[4]) if fetch is not None else None
            return user

    @staticmethod
    def first(id=None, access_token=None, user_id=None, domain=None, avatar=None):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            sql = 'select id, access_token, user_id, domain, avatar from user'
            if id is not None:
                c.execute(sql+' where id=?', (id,))
            elif access_token is not None:
                c.execute(sql+' where access_token=?', (access_token,))
            elif user_id is not None and domain is not None:
                c.execute(sql+' where user_id=? and domain=?', (user_id, domain))
            elif avatar is not None:
                c.execute(sql+' where avatar=?', (avatar,))
            else:
                c.execute(sql)
            fetch = c.fetchone()
            user = User(fetch[0], fetch[1], fetch[2], fetch[3], fetch[4]) if fetch is not None else None
            return user

    @staticmethod
    def list():
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('select id, access_token, user_id, domain, avatar from user')
            fetch = c.fetchall()
            user_list = []
            for row in fetch:
                user = User(row[0], row[1], row[2], row[3], row[4])
                user_list.append(user)
            return user_list
