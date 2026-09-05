#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@File Name  : morning_check_service
@Author     : LeeCQ
@Date-Time  : 2026/9/6 

FastAPI实现以下接口搭建 ，我来做具体的实现
非GET接口需要接口鉴权

name 可选
GET /api/status?part=1&step=5&name=NameDemo
获取当前步骤的状态

POST /api/status?part=1&step=5&name=NameDemo 添加或更新当前步骤的状态
[{"name": "sub Step Name", "status": True, "exc": "期望值", "act": 实际值, "msg": "MSG"}, ...]


DELETE /api/status?part=1&step=5&name=NameDemo

GET /morning_check_{date:2020-09-06}.html

GET /morning_check?date=2020-09-06[默认当前日期]&type=json|html[默认html]
"""

from fastapi import FastAPI

app = FastAPI()
