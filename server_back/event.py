#!/usr/bin/python3
# -*- coding: utf-8
""" 
@File  : __init__.py.py
@Author: adam
@Date  : 2020/6/15 下午3:18
"""
import logging
import config
from aliyunamqp.rabbitmq import RabbitMQClient

logger = logging.getLogger(__name__)


class EventHandler(object):
    def __init__(self):
        self.rabbitmq_client = RabbitMQClient()

    """
    发送到用户交换机消息中间处理类
    """

    def join(self, data):
        """
        加入
        """
        send_data = {
            "type": "join",
            "data": data
        }
        self.rabbitmq_client.publish_message(send_data, config.WEBSOCKET_LISTEN_EXCHANGE,
                                             config.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')

    def leave(self, data):
        """
        离开房间
        """
        send_data = {
            "type": "leave",
            "data": data
        }
        self.rabbitmq_client.publish_message(send_data, config.WEBSOCKET_LISTEN_EXCHANGE,
                                             config.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')

    def nicks(self, data):
        """
        在线人员
        """
        send_data = {
            "type": "nicks",
            "data": data
        }
        self.rabbitmq_client.publish_message(send_data, config.WEBSOCKET_LISTEN_EXCHANGE,
                                             config.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')

    def send_message(self, data):
        """
        发送消息
        """
        send_data = {
            "type": "send_message",
            "data": data
        }
        self.rabbitmq_client.publish_message(send_data, config.WEBSOCKET_LISTEN_EXCHANGE,
                                             config.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')

    def heartbeat(self, data):
        """
        心跳
        """
        send_data = {
            "type": "heartbeat",
            "data": data
        }
        self.rabbitmq_client.publish_message(send_data, config.WEBSOCKET_LISTEN_EXCHANGE,
                                             config.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')


def recursive_unicode(obj):
    """Walks a simple data structure, converting byte strings to unicode.

    Supports lists, tuples, and dictionaries.
    """
    if isinstance(obj, dict):
        return dict((recursive_unicode(k), recursive_unicode(v)) for (k, v) in obj.items())
    elif isinstance(obj, list):
        return list(recursive_unicode(i) for i in obj)
    elif isinstance(obj, tuple):
        return tuple(recursive_unicode(i) for i in obj)
    elif isinstance(obj, bytes):
        return obj.decode("utf-8")
    else:
        return obj
