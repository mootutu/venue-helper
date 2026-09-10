#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @File    : settings.py
'''
    CGDM: 场馆代码
    XMDM: 项目代码
    XQWID: 校区唯一标识 (1粤海, 2丽湖)
    KYYSJD: 可预约时间段 (形如20:00-21:00)
    YYRQ: 预约日期 例如 2025-01-01
    YYLX: 预约类型 即订场方式(1.0: 包场, 2.0: 散场 )
'''
# courses=[{"CGDM":"001","CDWID":"6fbd613382ef48db9d2a2d214e47bae3","XMDM":"001","XQWID":"1","KYYSJD":"20:00-21:00","YYRQ":"2025-04-29","YYLX":"1.0"}]  # 预约场次列表
counts = 10 # 预约总轮次
courses = [
    {"CGDM":"004", "XMDM":"007", "XQWID":"1", "KYYSJD":"16:00-17:00", "YYRQ":"2026-09-03", "YYLX":"2.0"},
]  # 一楼重量型健身，粤海校区，散场；不填CDWID则自动轮询可用场地
# courses=[{"CGDM":"008","XMDM":"006","XQWID":"1","KYYSJD":"20:00-21:00","YYRQ":"2026-04-16","YYLX":"1.0"}]  # 预约场次列表
delay = 200  # 延迟时间, 单位毫秒
# stuid = 2500101041
# stuname = "王伟钦"
# stuid = 2500101069
# stuname = "郑凯杰"
stuid = 2024000814
stuname = "王祎乐"
# 使用用户最新提供的登录 cookies
cookies = 'EMAP_LANG=zh; _WEU=LiB2T5W5eSwO80fmDNkSjyPrEaW3GcRmkd9BmwGnWl43vAp6pqWK2tZy11xIlhUL3ujF76RRb5UB*i_T9IR2KKGSu5LSAvE*13IX69lh3GTivlwvqDUh29P1eQOzNEvSYxK_0N4f_OdzsA7GGwPTTFVgLNkoWl5TKMzArRCxYuLku3ujTA9yIBadSod1eGL1peM9qPHV1*jlMgrjL6w6sKH3*LjiAHRv; amp.locale=undefined; insert_cookie=38189586; asessionid=98dbc08b-f62e-4d9b-b8eb-e5e651b0fd38; MOD_AUTH_CAS=MOD_AUTH_ST-1072570-ChhlFstO8xLRORyZ1ZqWgBfewPwciapserver4; route=f9bb7d1dbb51bc04862ec2b9cddaff48'

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
