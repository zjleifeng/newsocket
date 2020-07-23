#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : settings.py
@Author: adam
@Date  : 2019/12/23 下午4:32
'''
from __future__ import unicode_literals, absolute_import

import logging.config
import os

# 当前目录路径上一级
BASE_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
# 日志所在目录
LOG_PATH = os.path.join(BASE_PATH, 'logs')
# 临时存储目录
TEMP_PATH = os.path.join(BASE_PATH, 'temp')

# 是否调试模式
DEBUG = False

# 密码加密是的SECRET
SECRET_KEY = "d2)=d$mwke6g349p&(8n0*10)_kyg(w38$jf67jp(fmpug3_a^"

# mysql数据库配置
MYSQL_DB_HOST = "127.0.0.1"
MYSQL_DB_PORT = 3306
MYSQL_DB_DBNAME = "websoc"
MYSQL_DB_USER = "root"
MYSQL_DB_PASSWORD = "123"
MYSQL_IDLE_CONNECTIONS = 2000
MYSQL_MAX_RECYCLE_SEC = 600  # tornado_pymysql 连接池连接回收时间 单位:秒
MYSQL_CHARSET = "utf8mb4"
MYSQL_MAX_RECYCLE_TIMES = 50  # DButils 连接池,连接池连接回首次数
# mincached : 启动时开启的闲置连接数量(缺省值 0 以为着开始时不创建连接)
MYSQL_MIN_CACHED = 10
# maxcached : 连接池中允许的闲置的最多连接数量(缺省值 0 代表不闲置连接池大小)
MYSQL_MAX_CACHED = 50

REDIS_HOST = "127.0.0.1"
REDIS_PASS = ""
REDIS_DB = 0
REDIS_PORT = 6379
REDIS_MAX_CONNECTIONS = 10000

RABBIT_MQ_HOST = "**"
RABBIT_MQ_PORT = 5672
virtualHost = "**"
accessKey = "**"
# 阿里云的accessSecret
accessSecret = "**"
# 主账号id
resourceOwnerId = 1570517735127118

# RabbitMQ相关队列配置
WEBSOCKET_SEND_EXCHANGE = "websocket_send_exchange"
WEBSOCKET_LISTEN_EXCHANGE = "websocket_listen_exchange"

#: 长连接配置要求
MAX_ROOMS = 100  # 单进程最大房间数
MAX_USERS_PER_ROOM = 10000  # 单进程最大用户数

HOST = '0.0.0.0'
PORT = 9100

# 代码修改后是否自动重启
AUTO_RELOAD = True if DEBUG else False

# 日志模块配置
LOGGING_LEVEL = 'DEBUG' if DEBUG else 'INFO'
LOGGING_HANDLERS = ['console'] if DEBUG else ['file']
if not os.path.exists(LOG_PATH):
    # 创建日志文件夹
    os.makedirs(LOG_PATH)

if not os.path.exists(TEMP_PATH):
    # 创建日志文件夹
    os.makedirs(TEMP_PATH)

file_log_handler = {
    'level': 'DEBUG',
    'filename': os.path.join(LOG_PATH, 'server.log'),
    'formatter': 'verbose'
}
try:
    import cloghandler

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
# 执行自定义配置 如数据库等相关配置, 放在日志配置之前的原因,是日志会根据DEBUG变化而变化
etc_path = os.path.join(BASE_PATH, "etc", 'cfg.py')
if os.path.exists(etc_path):
    file = open(etc_path, 'r')
    text = file.read()
    file.close()
    try:
        exec(text)
    except Exception as e:
        print(e)
