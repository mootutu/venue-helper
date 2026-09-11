#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @File    : settings.py
import os
'''
    CGDM: 场馆代码
    XMDM: 项目代码
    XQWID: 校区唯一标识 (1粤海, 2丽湖)
    KYYSJD: 可预约时间段 (形如20:00-21:00)
    YYRQ: 预约日期 例如 2025-01-01
    YYLX: 预约类型 即订场方式(1.0: 包场, 2.0: 散场 )
'''
# courses=[{"CGDM":"001","CDWID":"6fbd613382ef48db9d2a2d214e47bae3","XMDM":"001","XQWID":"1","KYYSJD":"20:00-21:00","YYRQ":"2025-04-29","YYLX":"1.0"}]  # 预约场次列表
counts = int(os.getenv("VENUE_COUNTS", "10")) # 预约总轮次
# 课程应由 WebUI/交互式启动流程提供，避免在仓库中保存个人预约信息。
courses = []
# courses=[{"CGDM":"008","XMDM":"006","XQWID":"1","KYYSJD":"20:00-21:00","YYRQ":"2026-04-16","YYLX":"1.0"}]  # 预约场次列表
delay = 200  # 延迟时间, 单位毫秒
# stuid = 2500101041
# stuname = "王伟钦"
# stuid = 2500101069
# stuname = "郑凯杰"
stuid = os.getenv("VENUE_STUID", "")
stuname = os.getenv("VENUE_STUNAME", "")
# 登录 cookies 仅从环境变量读取：VENUE_COOKIES='key=value; ...'
cookies = os.getenv("VENUE_COOKIES", "")

if isinstance(cookies, str):
    cookie_list = cookies.split(';')
    cookies = {}
    for item in cookie_list:
        item = item.strip()
        if not item or "=" not in item:
            continue
        key, value = item.split('=', 1)
        cookies[key] = value
if not isinstance(cookies, dict):
    raise ValueError("invalid cookie!")

headers = {
    'Accept': '*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
    'Origin': 'https://ehall.szu.edu.cn',
    'Pragma': 'no-cache',
    'Referer': 'https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/index.do?t_s=1745831680729',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
}
