#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : views.py
@Author: adam
@Date  : 2019/12/23 下午5:19
'''
import logging
from concurrent.futures import ThreadPoolExecutor
import uuid
import tornado.web
from tornado.concurrent import run_on_executor
from tornado.escape import json_decode
from tornado.gen import coroutine
from config import settings
from utils.rabbitmq import RabbitMQClient
from utils.room_handler import rlock
from utils.tornado.web import BaseWebsocketHandler, BaseRequestHandler, RequestHandler
import json
from config.redis import RedisClient
import time, datetime

logger = logging.getLogger(__name__)


class YouinUserHandler(BaseWebsocketHandler):
    executor = ThreadPoolExecutor()

    def initialize(self, room_handler):
        self.room_handler = room_handler

    @coroutine
    def open(self, *args, **kwargs):
        """
        初始化时，确定用户信息
        """
        user_id = args[1]
        if user_id == "false" or not user_id:
            user_id = str(uuid.uuid4().int)
        self.user_id = user_id
        self.room = args[0]
        self.client_id = self.room_handler.add_room(self.room, self.user_id)
        with rlock:
            logger.info("add_client_id:{}".format(self.client_id))
            result = self.room_handler.add_client(self.client_id, self)

        send_data = {
            "type": "join",
            "data": result
        }
        # 通知同一房间所有人某人加入
        yield self.publish_message(send_data, settings.WEBSOCKET_SEND_EXCHANGE, settings.WEBSOCKET_SEND_EXCHANGE)


    @coroutine
    def on_message(self, message):
        """
        收到发送消息通知
        通知在房间的所有用户
        """
        try:
            msg = json_decode(message)
            e_type = msg.get("type")
            t_data = msg.get("msg")
            msg_type = msg.get("msg_type")
            client_info = self.room_handler.clients_info.get(self.client_id)
            if e_type == "message":
                if client_info:
                    room = client_info['room']
                    user_id = client_info['user_id']

                    event_data = {}
                    event_data['room'] = room
                    event_data['user_id'] = user_id
                    event_data['msg_type'] = msg_type
                    event_data['msg'] = t_data

                    send_data = {
                        "type": "send_message",
                        "data": event_data
                    }
                    yield self.publish_message(send_data, settings.WEBSOCKET_SEND_EXCHANGE,
                                               settings.WEBSOCKET_SEND_EXCHANGE)

                else:
                    logger.error("收到用户[{}]信息，但本地信息不存在 [{}]".format(self.client_id, self.room_handler.clients_info))
            elif e_type == "heartbeat":
                send_data = {
                    "type": "heartbeat",
                    "data": {
                        "room": client_info['room'],
                        "user_id": client_info['user_id'],
                        "client_id": self.client_id
                    }
                }
                yield self.publish_message(send_data, settings.WEBSOCKET_SEND_EXCHANGE,
                                           settings.WEBSOCKET_SEND_EXCHANGE)
            # 记录数据到数据库
            elif e_type == "record":
                if msg_type == "start":
                    nowtime = str(round(time.time()))
                    self.redis.hset(name="{}_static_info".format(client_info['room']), key=self.client_id,
                                    value=json.dumps(dict(start_time=nowtime, user_id=self.user_id)))
                elif msg_type == "end":
                    # 更新用户离开时间hash
                    has_data = self.redis.hget(name="{}_static_info".format(client_info['room']), key=self.client_id)
                    has_data_str = str(has_data, encoding="utf-8")
                    js_data = json.loads(has_data_str)
                    js_data["end_data"] = round(time.time())
                    self.redis.hset(name="{}_static_info".format(client_info['room']), key=self.client_id,
                                    value=json.dumps(js_data))

            else:
                logger.warning("暂时不支持的类型 type={}".format(e_type))
        except:
            logger.exception("处理事件失败")

    @coroutine
    def on_ping(self, data):
        print('ping:', data)
        pass

    @coroutine
    def on_pong(self, data):
        print(datetime.datetime.now())
        print('pong:', data)
        if not data:
            byte_ping = round(time.time() * 1000).to_bytes(13, 'big')
            self.ping(byte_ping)
        pass

    @coroutine
    def on_close(self):
        """
        关闭或者断开连接
        :return:
        """
        result = self.room_handler.remove_client(self.client_id)

        # 离开房间
        yield self.publish_message(msg_type="leave")
        send_data = {
            "type": "leave",
            "data": result
        }
        yield self.publish_message(send_data, settings.WEBSOCKET_SEND_EXCHANGE, settings.WEBSOCKET_SEND_EXCHANGE)

    def check_origin(self, origin):
        """
        校验来源
        :param origin:
        :return:
        """
        return True

    # 单机不使用amqp发送数据
    # @run_on_executor
    # def publish_message(self, msg_type,data=None):
    #     self.room_handler.send_msg(self.client_id, msg_type=msg_type,message=data)

    @run_on_executor
    def publish_message(self, data, exchange_name, routing_key):
        rmq_client = RabbitMQClient()
        rmq_client.publish_message(data, exchange_name, routing_key, exchange_type='direct')


class MainHandler(BaseRequestHandler):

    def initialize(self, room_handler):
        self.room_handler = room_handler

    def get(self, *args, **kwargs):
        """
        :param args:
        :param kwargs:
        :return:
        """

        try:
            #: 房间名字
            room = self.get_argument('room')
            #: 用户名字
            self.render("home.html", room_name=room)
        except tornado.web.MissingArgumentError:
            self.render("login.html")
        except RuntimeError as e:
            self.render("error.html", msg=str(e))


class ConcurrentView(RequestHandler):
    """
    获取当前room单的并发人数
    """

    def get(self, *args, **kwargs):
        myredis = RedisClient.get_client()
        room = args[0]
        room_md5 = "{}_concurrent_user".format(room)
        # room_md5 = hashlib.md5(room.encode('utf-8')).hexdigest()
        nicks = myredis.llen(room_md5)
        alluserkey = "{}_all_user_id".format(room)
        user_count = myredis.scard(alluserkey)
        data = {"in_user_count": nicks, "all_user_count": user_count}
        # self.write(json.dumps(data, ensure_ascii=False))
        self.render("count.html", inuser=nicks, alluser=user_count, room_name=room)


class AllUserCountView(RequestHandler):
    """
    获取当前room总计入人数
    """

    def get(self, *args, **kwargs):
        myredis = RedisClient.get_client()
        room = args[0]
        key = "{}_all_user_id".format(room)
        user_count = myredis.scard(key)
        print(user_count)
        data = {"allcount": user_count}
        self.write(json.dumps(data, ensure_ascii=False))
