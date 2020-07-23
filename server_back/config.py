#!/usr/bin/python3
# -*- coding: utf-8
""" 
@File  : __init__.py.py
@Author: adam
@Date  : 2020/6/15 下午3:17
"""
import logging.config
import os

# 当前目录路径
BASE_PATH = os.path.abspath(os.path.dirname(__file__))
# 日志所在目录
LOG_PATH = os.path.join(BASE_PATH, 'logs')
# 临时存储目录
TEMP_PATH = os.path.join(BASE_PATH, 'temp')

DEBUG = False

# 阿里云AMQP配置
RABBIT_MQ_HOST = "**"
RABBIT_MQ_PORT = 5672
virtualHost = "**"
accessKey = "**"
# 阿里云的accessSecret
accessSecret = "**"
# 主账号id
resourceOwnerId = 1570517735127118
# amqp中转交换机
WEBSOCKET_SEND_EXCHANGE = "websocket_send_exchange"
# amqp订阅交换机
WEBSOCKET_LISTEN_EXCHANGE = "websocket_listen_exchange"

# 日志模块配置
LOGGING_LEVEL = 'DEBUG' if DEBUG else 'INFO'
LOGGING_HANDLERS = ['console'] if DEBUG else ['file']

if not os.path.exists(LOG_PATH):
    os.makedirs(LOG_PATH)

if not os.path.exists(TEMP_PATH):
    os.makedirs(TEMP_PATH)

file_log_handler = {
    'level': 'DEBUG',
    'filename': os.path.join(LOG_PATH, 'server.log'),
    'formatter': 'verbose'
}
try:
    log_handler = {
        'class': 'cloghandler.ConcurrentRotatingFileHandler',
        # 当达到5MB时分割日志
        'maxBytes': 1024 * 1024 * 5,
        'backupCount': 10,
        'delay': True,
    }
except:
    log_handler = {
        'class': 'logging.handlers.TimedRotatingFileHandler'
    }

file_log_handler.update(log_handler)

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(process)d] [%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%Y-%m-%d %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': file_log_handler
    },
    'loggers': {
        'tornado.curl_httpclient': {
            'handlers': LOGGING_HANDLERS,
            'level': 'INFO',
        },
        '': {
            'handlers': LOGGING_HANDLERS,
            'level': LOGGING_LEVEL,
        },
    }
})
