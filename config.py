import configparser

_config = configparser.ConfigParser()
_config.read('config.ini')

def config(key):
    if key not in _config['config']:
        return None
    return _config['config'][key]
