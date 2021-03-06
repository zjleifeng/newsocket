#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : server.py
@Author: adam
@Date  : 2019/12/23 下午4:32
'''
import logging
from tornado.options import options, define
from tornado.escape import native_str, recursive_unicode, json_decode
from config import settings
import asyncio
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado import httpserver, ioloop
import threading
import tornado.web
import os
from config.mysql import MySQLPOOL
from config.redis import RedisClient
import importlib
import signal
from utils.rabbitmq import RabbitMQClient
import time
import getopt, sys
from utils.room_handler import event_handler

define("port", default=settings.PORT, help=u"run port", type=int)
define("host", default=settings.HOST, help=u"run host", type=str)

logger = logging.getLogger(__name__)
MAX_WAIT_SECONDS_BEFORE_SHUTDOWN = 1


class MyApplication(tornado.web.Application):
    """
    自定义Application
    添加redis
    添加db
    """

    def __init__(self, default_host=None, transforms=None,
                 **app_settings):
        handlers = self._import_handlers()
        default_settings = {
            "cookie_secret": 'WsflEue2Q1WUFbhYhou2vtsq8cMS2knhiWdcfw7pnq0=',
            "xsrf_cookies": False,
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
            "websocket_ping_interval" :10,
            "websocket_ping_timeout":30
        }
        default_settings.update(app_settings)
        super(MyApplication, self).__init__(handlers, default_host, transforms, **default_settings)
        self.db = MySQLPOOL
        self.redis = RedisClient

    def _import_handlers(self):
        """
        动态导入tornado的处理类
        :param app:
        :return:
        """
        handlers = []
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        files = os.walk(os.sep.join([curr_dir, "handlers"]))
        for root, paths, fs in files:
            if "urls.py" in fs:
                module_name = root.split(os.sep)[-1]
                module_path = "handlers." + module_name + ".urls"
                module = importlib.import_module(module_path)
                urls = getattr(module, 'urls', None)
                if urls:
                    handlers.extend(urls)
        return handlers


def sig_handler(sig, frame):
    logger.warning('caught signal: %s', sig)
    tornado.ioloop.IOLoop.instance().add_callback(shutdown)


def shutdown():
    logger.info('stopping http server')
    server.stop()
    logger.info('will shutdown in %s seconds...', MAX_WAIT_SECONDS_BEFORE_SHUTDOWN)
    deadline = time.time() + MAX_WAIT_SECONDS_BEFORE_SHUTDOWN
    io_loop = tornado.ioloop.IOLoop.instance()

    def stop_loop():
        now = time.time()
        if hasattr(io_loop, "_callbacks"):
            if now < deadline and (io_loop._callbacks or io_loop._timeouts):
                io_loop.add_timeout(now + 1, stop_loop)
            else:
                io_loop.stop()
                logger.info('shutdown')
        else:
            io_loop.stop()
            logger.info('shutdown')

    stop_loop()


def rabbitmq_callback(ch, method, properties, body):
    """
        @ch: channel 通道，是由外部调用时上送
        out body
        读取队列内容做不同的操作
    """
    d_item = {}
    try:
        d_item = json_decode(recursive_unicode(body))
        h_type = d_item['type']
        h_data = d_item['data']
        if hasattr(event_handler, h_type):
            try:
                logger.info("收到[{}]请求,数据为[{}] ".format(h_type, h_data))
                func = getattr(event_handler, h_type)
                func(h_data)
            except:
                logger.exception("处理失败 [{}]".format(d_item))
        else:
            logger.error("暂时不支持的操作类型[{}] 操作内容[{}]".format(h_type, h_data))
    except:
        logger.exception("解析内容失败：{}".format(d_item))


def listen_rabbitmq():
    """
    监听rabbitmq的通知，用于分布式websocket消息处理
    :return:
    """
    conn = None
    try:
        client = RabbitMQClient()
        # 获取一个扇形交换机的channel
        conn, channel = client.get_channel(settings.WEBSOCKET_LISTEN_EXCHANGE, exchange_type='fanout')

        # 声明临时队列 , param exclusive 互斥
        tmp_queue = channel.queue_declare(exclusive=True)
        queue_name = tmp_queue.method.queue

        # 对绑定交换机和路由
        channel.queue_bind(exchange=settings.WEBSOCKET_LISTEN_EXCHANGE,
                           queue=queue_name,
                           routing_key=settings.WEBSOCKET_LISTEN_EXCHANGE)
        # 在队列中读取信息，交给回调处理
        channel.basic_consume(rabbitmq_callback, queue=queue_name, no_ack=True)
        channel.start_consuming()
    except Exception as e:
        logger.exception("处理失败:{}".format(e))
    finally:
        if conn:
            conn.close()



def io_loop_start():
    global server
    # 增加调度进程，用于分布式接收和发送ws相关数据
    if not settings.DEBUG:
        # DEBUG模式时不启动线程，测试环境及生产环境时需要，本地测试时不需要启动
        t1 = threading.Thread(target=listen_rabbitmq, name='listen_rabbitmq', daemon=True)
        t1.start()
    # 启动进程
    app = MyApplication()
    server = httpserver.HTTPServer(app, xheaders=True)
    myport = options.port
    opts, argvs = getopt.getopt(sys.argv[1:], "p:")
    print(opts)
    for op, value in opts:
        if op == '-p':
            myport = int(value)

    logger.info('server is running on %s:%s' % (myport, options.host))
    server.listen(myport, options.host)
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)


def main():
    # 重新设置一下日志级别，默认情况下，tornado 是 info
    # py2 下 options.logging 不能是 Unicode
    print("start")

    options.logging = native_str(settings.LOGGING_LEVEL)
    try:
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
    except:
        logger.exception("use uvloop error")
    # 绑定服务端web监听端口
    io_loop_start()
    # 启动事件循环
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
