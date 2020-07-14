#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : redis.py
@Author: adam
@Date  : 2019/12/23 下午4:32
'''
import redis

from config import settings


class RedisClient(object):
    _client = None

    def __init__(self):
        if self._client is None:
            self._create_redis_client()

    @classmethod
    def _create_redis_client(cls):
        """
        创建连接
        :return:
        """
        RedisClient._client = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT,
            db=settings.REDIS_DB, password=settings.REDIS_PASS)

    @classmethod
    def get_client(cls):
        if RedisClient._client is None:
            cls._create_redis_client()
        return RedisClient._client
