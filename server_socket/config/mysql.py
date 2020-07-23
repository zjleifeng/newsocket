#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : mysql.py
@Author: adam
@Date  : 2019/12/23 下午4:32
'''
import logging
from sqlalchemy.ext.declarative import declarative_base
from config import settings
from sqlalchemy import create_engine

Base = declarative_base()
logger = logging.getLogger(__name__)

engine = create_engine(
    "mysql://{}:{}@{}/{}?charset=utf8mb4".format(settings.WEBSOCKET_MYSQL_DB_USER, settings.WEBSOCKET_MYSQL_DB_PASSWORD,
                                                 settings.WEBSOCKET_MYSQL_DB_HOST, settings.WEBSOCKET_MYSQL_DB_DBNAME),
    encoding='utf-8', echo=False, pool_size=100, pool_recycle=3600)
