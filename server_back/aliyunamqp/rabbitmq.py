#!/usr/bin/python3
# -*- coding: utf-8
'''
@File  : rabbitmq.py
@Author: adam
@Date  : 2019/12/19 下午2:01
'''
import json
import logging
import pika
from aliyunamqp.AliyunCredentialsProvider2 import AliyunCredentialsProvider
import config

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """
    消息队列
    """

    def __init__(self, host=config.RABBIT_MQ_HOST, port=config.RABBIT_MQ_PORT, virtualHost=config.virtualHost):
        self.host = host
        self.port = port
        self.virtualHost = virtualHost
        self.provider = AliyunCredentialsProvider(config.accessKey, config.accessSecret, config.resourceOwnerId)

    def get_conn(self):
        credentials = pika.PlainCredentials(self.provider.get_username(), self.provider.get_password(),
                                            erase_on_connect=True)
        return pika.BlockingConnection(pika.ConnectionParameters(self.host, self.port, self.virtualHost, credentials))

    def get_channel(self, exchange_name, exchange_type='direct'):
        """
        创建交换机、声明一个直连的交换机
        """
        conn = self.get_conn()
        channel = conn.channel()
        channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type)
        return channel

    def publish_message(self, message, exchange_name, rounting_key="", exchange_type="direct"):
        """
        发送消息
        """
        channel = self.get_channel(exchange_name, exchange_type)
        message = json.dumps(message)
        channel.basic_publish(exchange=exchange_name,
                              routing_key=rounting_key,
                              body=message)
