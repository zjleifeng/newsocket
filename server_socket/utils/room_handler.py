#!/usr/bin/python3
# -*- coding: utf-8
""" 
@File  : room_handler.py
@Author: adam
@Date  : 2019/12/23 下午5:19
"""

import datetime
import hashlib
import json
import logging
import re
import threading
import time
import uuid

from tornado.escape import json_encode, recursive_unicode

from config import settings
from config.redis import RedisClient

logger = logging.getLogger(__name__)


class RoomHandler(object):
    def __init__(self):
        # 房间信息
        self.rooms_info = dict()
        # 临时连接信息
        self.temp_conns = dict()
        # 客户端信息
        self.clients_info = dict()
        self.redis = RedisClient.get_client()

    def add_room(self, room, user_id):
        """
        添加Room:
        1. 校验room相关信息
        2. 初始化room队列，并在pending中增加room信息，待到实际连接时再添加到room中
        3. 返回client_id，用于前台使用
        :param room: 房间名字
        :param nick: 用户名字
        :return: client_id
        """
        #: 校验房间和用户昵称的规则
        roomvalid = re.match(r'[\w-]+$', room)
        uservalid = re.match(r'[\w-]+$', user_id)
        if roomvalid == None:
            raise RuntimeError(
                "未检测到房间号，房间号由大小写字母、数字、-、_组成.")
        if uservalid == None:
            raise RuntimeError(
                "未检测到用户id，由大小写字母、数字、-、_组成.")

        # 校验是否满足需求（数量限制，名字限制）
        with rlock:
            # #: 校验是否单台服务器已经超限
            # if len(self.rooms_info) > settings.MAX_ROOMS:
            #     raise RuntimeError("当前服务器已达最大房间数,{}".format(settings.MAX_ROOMS))
            # #: 校验是否房间人员已经超限
            # if room in self.rooms_info and len(
            #         self.rooms_info[room]) >= settings.MAX_USERS_PER_ROOM:
            #     raise RuntimeError("当前最大连接人数超过限制{}".format(settings.MAX_USERS_PER_ROOM))
            # 添加到房间中
            client_id = str(uuid.uuid4().int)
            if not self.rooms_info.get(room):
                self.rooms_info[room] = []
            # 验证nick是否已经重复
            # nicks = list(map(lambda x: x['nick'], self.rooms_info[room]))
            # room_md5 = hashlib.md5(room.encode('utf-8')).hexdigest()
            # nicks = recursive_unicode(self.redis.lrange(room_md5, 0, self.redis.llen(room_md5)))
            # suffix = 1
            # while True:
            #     if nick in nicks:
            #         nick += str(1)
            #     else:
            #         break
            #     suffix += 1

            # 将客户端的信息保存至temp_conns中
            self.temp_conns[client_id] = dict(room=room,user_id=user_id)
            # self.redis.hset(name="temp_conns", key=client_id, value=json.dumps(dict(room=room, user_id=user_id)))
            return client_id

    def add_client(self, client_id, wsconn):
        """
        添加client_ws_conn
        1. 删除pending中的client
        2. 在room中实际添加连接
        3. 在client中实际添加信息
        4. 向房间所有人广播信息，同时更新房间人数列表
        :param client_id:
        :param wsconn:
        :return:
        """
        with rlock:
            # 在临时中取出client信息，并添加到clients_info中
            logger.info("pop_client_id:{}".format(client_id))
            client_info = self.temp_conns.pop(client_id)
            # client_info_b = self.redis.hget('temp_conns', client_id)
            # client_info = json.loads(recursive_unicode(client_info_b))
            # if client_info:
            #     res = self.redis.hdel('temp_conns', client_id)
            #     logger.info("删除临时temp_conns:{}".format(res))

            client_info['conn'] = wsconn
            self.clients_info[client_id] = client_info
            self.user_id=client_info['user_id']
            # 在room中添加上连接信息
            self.rooms_info[client_info['room']].append(dict(
                user_id=self.user_id,
                conn=wsconn,
                client_id=client_id
            ))


            # 存储房间所进入过的人和时间list
            #nowtime=str(round(time.time()))#当前秒时间戳
            #in_data={"client_id":client_id,"start_time":nowtime,"user_id":self.user_id}
            #in_key="{}_all_user".format(client_info['room'])
            #self.redis.rpush(in_key,json.dumps(in_data))

            # 存储redis进入房间的人以及时间Hash
            #self.redis.hset(name="{}_static_info".format(client_info['room']), key=client_id, value=json.dumps(dict(start_time=nowtime,user_id=self.user_id)))


            # 用户列表放入redis缓存中
            # room_md5 = hashlib.md5(client_info['room'].encode('utf-8')).hexdigest()
            room_md5="{}_concurrent_user".format(client_info['room'])
            self.redis.rpush(room_md5, self.user_id)

            #存储所有来过的用户set去重
            self.redis.sadd("{}_all_user_id".format(client_info['room']),self.user_id)
            # 获取在线用户列表
            # nicks = recursive_unicode(self.redis.lrange(room_md5, 0, self.redis.llen(room_md5)))
        return {"room": client_info['room'], "user_id": self.user_id}

    def remove_client(self, client_id):
        """
        1. 在clients_info中移除client_id
        2. 在rooms_info中移除client，若是房间里没有人了，房间一并删除
        3. 通知房间内所有人。**离开房间
        4. 刷新房间在线人数列表
        :param client_id: 根据client_id通知信息
        :return:
        """
        # 在clients_info中移除client_id
        if client_id not in self.clients_info:
            return

        with rlock:
            client_info = self.clients_info.get(client_id)
            room = client_info['room']
            user_id = client_info['user_id']

            # 在rooms_info中移除room中的client
            room_client = list(filter(lambda x: x['client_id'] == client_id,
                                      self.rooms_info[room]))

            # 在redis中，将对应的用户移除
            room_md5="{}_concurrent_user".format(room)
            # room_md5 = hashlib.md5(room.encode('utf-8')).hexdigest()
            self.redis.lrem(room_md5, 0, user_id)

            # #更新用户离开时间hash
            # has_data=self.redis.hget(name="{}_static_info".format(client_info['room']), key=client_id)
            # has_data_str=str(has_data, encoding = "utf-8")
            # js_data=json.loads(has_data_str)
            # js_data["end_data"]=round(time.time())
            # self.redis.hset(name="{}_static_info".format(client_info['room']), key=client_id, value=json.dumps(js_data))

            # 获取房间列表
            # nicks = recursive_unicode(self.redis.lrange(room_md5, 0, self.redis.llen(room_md5)))
            # 将当前client在rooms中移除
            self.rooms_info[room].remove(room_client[0])

            # 将client在clients中移除
            del self.clients_info[client_id]

            # 移除room
            if len(self.rooms_info[room]) == 0:
                del self.rooms_info[room]

        return {"room": room, "user_id": user_id}

    def send_msg(self, client_id, msg_type="join", message=None):
        """
        :param client_id: 客户端ID
        :param msg_type: 发送消息类型  join, leave, nicks
        :return:
        """
        client_info = self.clients_info.get(client_id)
        if client_info:
            room = client_info['room']
            user_id = client_info['user_id']
            conns = list(map(lambda x: x['conn'], self.rooms_info[room]))
            msg = dict(time='%10.6f' % time.time(),
                       msg_type=msg_type)
            if msg_type.lower() == 'join':
                msg['user_id'] = user_id
                msg['msg'] = '{} joined the chat room.'.format(user_id)
            elif msg_type.lower() == 'leave':
                msg['user_id'] = user_id
                msg['msg'] = '{} left the chat room.'.format(user_id)
            elif msg_type.lower() == 'nicks':
                msg['user_id'] = user_id
                msg['msg'] = "当前并发:{}".format(len(self.rooms_info[room]))
                # msg['msg'] = list(
                #     map(lambda x: x['nick'], self.rooms_info[room]))
            elif msg_type.lower() == 'msg':
                msg['user_id'] = user_id
                msg['msg'] = message
            elif msg_type.lower() == 'heartbeat':
                msg['user_id'] = user_id
                msg['user_id'] = user_id
                msg['msg'] = "heartbeat"
                conn = client_info['conn']
                conn.write_message(msg)
                return ""
            else:
                msg['user_id'] = user_id
                msg['msg'] = message
            msg = json.dumps(msg)
            for conn in conns:
                conn.write_message(msg)



class EventHandler(object):
    """
        收到消息发送给前端的事件处理
    """

    def __init__(self, room):
        self.room = room

    def join(self, data):
        """
        加入房间，消息推送
        :param data:
        :return:
        """
        room_name = data['room']
        user_id = data['user_id']
        event_data = {
            "msg_type": "msg",
            "user_id": user_id,
            "msg": "加入了房间。",
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with rlock:
            rooms_info = self.room.rooms_info.get(room_name)
            if not rooms_info:
                logger.warning("无法获取到room信息[%s]" % rooms_info)
                return

            for client_info in rooms_info:
                ws_conn = self.room.clients_info.get(client_info['client_id'], None)
                if not ws_conn:
                    logger.warning("无法获取到用户信息[%s]" % client_info['client_id'])
                else:
                    ws_conn['conn'].write_message(json_encode(event_data))

    def send_message(self, data):
        """
        :param data:
        :return:
        """
        room_name = data['room']
        user_id = data['user_id']
        msg = data['msg']
        event_data = {
            "msg_type": "msg",
            "user_id": user_id,
            "msg": msg,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with rlock:
            rooms_info = self.room.rooms_info.get(room_name)
            if not rooms_info:
                logger.warning("无法获取到room信息[%s]" % rooms_info)
                return

            for client_info in rooms_info:
                ws_conn = self.room.clients_info.get(client_info['client_id'], None)
                if not ws_conn:
                    logger.warning("无法获取到用户信息[%s]" % client_info['client_id'])
                else:
                    ws_conn['conn'].write_message(json_encode(event_data))

    def leave(self, data):
        """
        :param data:
        :return:
        """
        room_name = data['room']
        user_id = data['user_id']
        event_data = {
            "msg_type": "msg",
            "user_id": user_id,
            "msg": "离开了房间。",
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with rlock:
            rooms_info = self.room.rooms_info.get(room_name)
            if not rooms_info:
                logger.warning("无法获取到room信息[%s]" % rooms_info)
                return

            for client_info in rooms_info:
                ws_conn = self.room.clients_info.get(client_info['client_id'], None)
                if not ws_conn:
                    logger.warning("无法获取到用户信息[%s]" % client_info['client_id'])
                else:
                    ws_conn['conn'].write_message(json_encode(event_data))

    def nicks(self, data):
        """
        :param data:
        :return:
        """
        nicks = data['nicks']
        user_id = data['user_id']
        room_name = data['room']
        event_data = {
            "msg_type": "nicks",
            "user_id": user_id,
            "msg": nicks,
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with rlock:
            rooms_info = self.room.rooms_info.get(room_name)
            if not rooms_info:
                logger.warning("无法获取到room信息[%s]" % rooms_info)
                return

            for client_info in rooms_info:
                ws_conn = self.room.clients_info.get(client_info['client_id'], None)
                if not ws_conn:
                    logger.warning("无法获取到用户信息[%s]" % client_info['client_id'])
                else:
                    ws_conn['conn'].write_message(json_encode(event_data))

    def heartbeat(self, data):
        """
        :param data:
        :return:
        """
        room_name = data['room']
        user_id = data['user_id']
        client_id = data['client_id']
        event_data = {
            "msg_type": "heartbeat",
            "user_id": user_id,
            "msg": "心跳",
            "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        with rlock:
            ws_conn = self.room.clients_info.get(client_id, None)
            if not ws_conn:
                logger.warning("无法获取到用户信息{}".format(client_id))
                return
            ws_conn['conn'].write_message(json_encode(event_data))


room_handler = RoomHandler()
event_handler = EventHandler(room_handler)
rlock = threading.RLock()
