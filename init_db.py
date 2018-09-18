import sqlite3
from contextlib import closing

dbname = 'database.db'

with closing(sqlite3.connect(dbname)) as conn:
    c = conn.cursor()

    create_table = '''create table oauth_applications (id integer PRIMARY KEY AUTOINCREMENT, domain varchar(256),
                      uid varchar(256), secret varchar(256))'''
    c.execute(create_table)
    create_table = 'create table uuid (uuid varchar(256), user_id varchar(256), domain varchar(256), disable boolean)'
    c.execute(create_table)
    create_table = 'create table access_token (id integer PRIMARY KEY AUTOINCREMENT, access_token varchar(256), user_id varchar(256), domain varchar(256), session_id varchar(256), avatar varchar(256))'
    c.execute(create_table)

    conn.commit()
