import sys
import os
import logging
import logging.config

LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
            'stream': sys.stdout,
        },
        'syslog': {
            'class': 'logging.handlers.SysLogHandler',
            'formatter': 'simple',
            'address':  ('localhost', 514),
            'facility': 'user',
        }
    },
    'formatters':{
        'simple':{
            'format': '%(asctime)s %(name)s [%(levelname)s] %(message)s',
        },
        'remote':{
            'format': '%(name)s:%(message)s'
        },
    },
    'loggers': {
    },
    'root': {
        'handlers': ['console', 'syslog'],
        'level': 'DEBUG'
    },
}

def config_log(mute_console=None):
    from aiobbox import testing
    logging_config = LOGGING.copy()

    handlers = ['syslog']
    
    if mute_console is None:
        mute_console = (
            os.getenv('BBOX_LOG_MUTE', '').lower()
            in ('1', 'true', 'yes'))

    if not mute_console:
        handlers.append('console')

    log_level = os.getenv('BBOX_LOG_LEVEL')
    if not log_level:
        if testing.test_mode:
            log_level = 'DEBUG'
        else:
            log_level = 'INFO'

    logging_config['root']['level'] = log_level
    logging_config['root']['handlers'] = handlers
    logging.config.dictConfig(logging_config)
