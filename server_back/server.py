#!/usr/bin/python3
# -*- coding: utf-8
""" 
@File  : server.py
@Author: adam
@Date  : 2019/12/24 上午9:50
"""
import json
import logging
import threading
import config
from event import EventHandler, recursive_unicode
from aliyunamqp.rabbitmq import RabbitMQClient

logger = logging.getLogger(__name__)


def rabbitmq_callback(ch, method, properties, body):
    """
    amqp回调函数
    """
    logger.info("开始处理消息")
    event_handler = EventHandler()
    d_item = json.loads((recursive_unicode(body)))
    logger.info("消息内容:{}".format(d_item))
    try:
        h_type = d_item['type']
        h_data = d_item['data']
        if hasattr(event_handler, h_type):
            func = getattr(event_handler, h_type)
            try:
                # 使用多线程处理
                t = threading.Thread(target=func, args=(h_data,))
                t.start()
            except Exception as e:
                logger.exception("多线程处理失败,error:{}, data:{}".format(e, h_data))
        else:
            logger.error("暂时不支持的操作类型[{}] 操作内容[{}]".format(h_type, h_data))
    except:
        logger.exception("解析内容失败：{}".format(d_item))


def run():
    conn = None
    try:
        client = RabbitMQClient()
        channel = client.get_channel(config.WEBSOCKET_SEND_EXCHANGE, exchange_type='direct')
        queue_name = '{}_task_queue'.format(config.WEBSOCKET_SEND_EXCHANGE)
        channel.queue_declare(durable=True, queue='{}_task_queue'.format(config.WEBSOCKET_SEND_EXCHANGE))

        channel.queue_bind(exchange=config.WEBSOCKET_SEND_EXCHANGE,
                           queue=queue_name,
                           routing_key=config.WEBSOCKET_SEND_EXCHANGE)
        # 在队列中读取信息
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(rabbitmq_callback, queue=queue_name, no_ack=True)
        channel.start_consuming()
    except:
        logger.exception("处理失败")
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run()
