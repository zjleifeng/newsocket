#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
@File  : urls.py
@Author: adam
@Date  : 2019/12/23 下午5:19
'''

from tornado.web import url

from utils.room_handler import room_handler
from handlers.ws.views import MainHandler,ConcurrentView,AllUserCountView,YouinUserHandler

urls = [
    url(r"/", MainHandler, {"room_handler": room_handler}),
    url(r"/youin/(\w+)/(\w+)/", YouinUserHandler, {"room_handler": room_handler}),#需要用户id
    url(r"/concurrent/(\w+)/", ConcurrentView),#get接口获取当前room并发人数
    url(r"/alluser/(\w+)/", AllUserCountView),  # get接口获取当前room总人数

]
