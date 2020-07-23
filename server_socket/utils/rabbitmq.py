#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : rabbitmq.py
@Author: adam
@Date  : 2019/12/23 下午4:48
'''
import logging

import pika
from tornado.escape import json_encode
from utils.AliyunCredentialsProvider2 import AliyunCredentialsProvider

from config import settings

LOGGER = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(self, host=settings.RABBIT_MQ_HOST, port=settings.RABBIT_MQ_PORT, virtualHost=settings.virtualHost):
        self.host = host
        self.port = port
        self.virtualHost = virtualHost
        self.provider = AliyunCredentialsProvider(settings.accessKey, settings.accessSecret, settings.resourceOwnerId)

    def get_conn(self):
        credentials = pika.PlainCredentials(self.provider.get_username(), self.provider.get_password(),
                                            erase_on_connect=True)
        return pika.BlockingConnection(pika.ConnectionParameters(self.host, self.port, self.virtualHost, credentials))

    def get_channel(self, exchange_name, exchange_type='fanout'):
        conn = self.get_conn()
        channel = conn.channel()
        channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type)
        return conn, channel

    def publish_message(self, message, exchange_name, rounting_key="", exchange_type="fanout"):
        """
        发送消息
        :param message:
        :param exchange_name:
        :param rounting_key:
        :param exchange_type:
        :return:
        """
        conn, channel = self.get_channel(exchange_name, exchange_type)
        message = json_encode(message)
        ret = channel.basic_publish(exchange=exchange_name,
                                    routing_key=rounting_key,
                                    body=message)
        conn.close()
