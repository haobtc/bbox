import sys
import os
import logging
import logging.config

'''
config logging from envs, the logging output to syslog instead by default
once the env BBOX_LOG_CONSOLE is set, logs can also be put to console
'''

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
            'address':  (os.getenv('BBOX_SYSLOG_DEST', 'localhost'), 514),
            'facility': 'user',
        }
    },
    'formatters':{
        'simple':{
            'format': '[%(asctime)s] %(name)s [%(levelname)s] %(message)s',
        },
        'remote':{
            'format': '%(name)s:%(message)s'
        },
    },
    'loggers': {
    },
    'root': {
        'handlers': ['syslog'],
        'level': 'DEBUG'
    },
}

def config_log():
    from aiobbox import testing
    logging_config = LOGGING.copy()

    handlers = ['syslog']

    log_to_console = (
        os.getenv('BBOX_LOG_CONSOLE', '').lower()
        in ('1', 'true', 'yes'))

    if log_to_console:
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
