import sqlite3
from contextlib import closing
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
dbname = config['config']['dbname']

class Zodiac:
    def __init__(self, id, title):
        self.id = id
        self.title = title

    def user_list(self):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('''select id, access_token, user.user_id, domain, avatar 
                         from user left join user_zodiac on user.id=user_zodiac.user_id 
                         where user_zodiac.zodiac_id=?''', (self.id,))
            fetch = c.fetchall()
            user_list = []
            for row in fetch:
                user_list.append(row)
            return user_list

    def add_user(self, user_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('insert into user_zodiac (user_id, zodiac_id) values (?,?)', (user_id, self.id))
            conn.commit()

    def del_user(self, user_id):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('delete user_zodiac where user_id=? and zodiac_id=?)', (user_id, self.id))
            conn.commit()

    @staticmethod
    def first(id=None, title=None):
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            sql = 'select id, title from zodiac'
            if id is not None:
                c.execute(sql+' where id=?', (id,))
            elif title is not None:
                c.execute(sql+' where title=?', (title,))
            else:
                c.execute(sql)
            fetch = c.fetchone()
            zodiac = Zodiac(fetch[0], fetch[1]) if fetch is not None else None
            return zodiac

    @staticmethod
    def list():
        with closing(sqlite3.connect(dbname)) as conn:
            c = conn.cursor()
            c.execute('select id, title from zodiac')
            fetch = c.fetchall()
            zodiac_list = []
            for row in fetch:
                zodiac = Zodiac(row[0], row[1])
                zodiac_list.append(zodiac)
            return zodiac_list
