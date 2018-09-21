import sqlite3
from contextlib import closing
from config import config

dbname = config('dbname')

with closing(sqlite3.connect(dbname)) as conn:
    c = conn.cursor()

    create_table = '''create table oauth_applications (id integer PRIMARY KEY AUTOINCREMENT, domain varchar(256),
                      uid varchar(256), secret varchar(256))'''
    c.execute(create_table)
    create_table = '''create table uuid (uuid varchar(256), user_id varchar(256), 
                      domain varchar(256), disable boolean)'''
    c.execute(create_table)
    create_table = '''create table user (id integer PRIMARY KEY AUTOINCREMENT, access_token varchar(256), 
                      user_id varchar(256), domain varchar(256), avatar varchar(256))'''
    c.execute(create_table)

    create_table = '''create table zodiac (id integer PRIMARY KEY AUTOINCREMENT, title varchar(256),
                      bot_access_token varchar(256), bot_base_url vasechar(256), uri varchar(256))'''
    c.execute(create_table)

    create_table = '''create table user_zodiac (user_id integer, zodiac_id integer, 
                      FOREIGN KEY(user_id) references user(id) ON DELETE CASCADE,
                      FOREIGN KEY(zodiac_id) references zodiac(id) ON DELETE CASCADE,
                      UNIQUE(user_id, zodiac_id))
                      '''
    c.execute(create_table)

    create_table = '''create table session (id integer PRIMARY KEY AUTOINCREMENT, 
                      session_id varchar(256), 
                      user_id integer,
                      FOREIGN KEY(user_id) references user(id) ON DELETE CASCADE)'''
    c.execute(create_table)

    insert_record = 'insert into zodiac (title) values ("general")'
    c.execute(insert_record)

    conn.commit()
