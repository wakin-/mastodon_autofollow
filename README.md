virtualenv env -p python3

pip install -r requirements.txt

vi config.ini
```
[config]
dbname = ****.db
server_domain = *****.***
server_secret_key = ***************************
max_login = 20
```

python init_db.py

add nginx conf
```
location /atlas {
  include uwsgi_params;
  uwsgi_pass unix:///tmp/flask_uwsgi.sock;
}
```
