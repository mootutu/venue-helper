#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""HTTP API client; credentials are injected at runtime by settings/UI."""
import json
import logging
import os
from typing import Any, Optional

import requests
from settings import cookies, headers, stuid, stuname

os.environ.setdefault("NO_PROXY", "ehall.szu.edu.cn")
logger = logging.getLogger(__name__)
_session = requests.Session()
REQUEST_TIMEOUT = (5, 15)


def _cookie_dict(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        result = {}
        for item in value.split(";"):
            if "=" in item:
                key, val = item.strip().split("=", 1)
                if key:
                    result[key] = val
        return result
    return {}


def _parse_json_response(response, action) -> Optional[Any]:
    if not (200 <= response.status_code < 300):
        logger.error("%s失败: HTTP status=%s", action, response.status_code)
        return None
    text = response.text.lstrip("\ufeff").strip()
    if not text:
        logger.error("%s失败: 响应体为空, status=%s", action, response.status_code)
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        logger.error("%s失败: 响应不是 JSON, status=%s", action, response.status_code)
        if "统一身份认证" in text or "<!DOCTYPE html" in text:
            logger.error("%s失败: cookies 可能已过期", action)
        return None
    return data


def _post_json(url, data, action):
    if data is not None and any(v is None for v in data.values()):
        logger.error("%s失败: 请求参数包含空值", action)
        return None
    try:
        _session.headers.clear()
        _session.headers.update(headers or {})
        _session.cookies.clear()
        _session.cookies.update(_cookie_dict(cookies))
        response = _session.post(url, data=data, timeout=REQUEST_TIMEOUT)
        return _parse_json_response(response, action)
    except requests.exceptions.RequestException as exc:
        logger.error("%s失败: %s", action, exc)
        return None


def getSysConfig():
    ret = _post_json("https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/getSportVenueData.do", None, "获取系统配置")
    if not isinstance(ret, dict):
        logger.error("获取系统配置失败: JSON 根节点不是对象")
        return None
    return ret


def getTimeList(XQ, YYRQ, YYLX, XMDM):
    if not all(str(v).strip() for v in (XQ, YYRQ, YYLX, XMDM)):
        logger.error("获取时间列表失败: 参数不能为空")
        return None
    return _post_json("https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/getTimeList.do", {
        'XQ': XQ, 'YYRQ': YYRQ, 'YYLX': YYLX, 'XMDM': XMDM}, "获取时间列表")


def getRoom(XMDM, YYRQ, YYLX, KSSJ, JSSJ, XQDM):
    if not all(str(v).strip() for v in (XMDM, YYRQ, YYLX, KSSJ, JSSJ, XQDM)):
        logger.error("获取场地列表失败: 参数不能为空")
        return None
    ret = _post_json("https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/modules/sportVenue/getOpeningRoom.do", {
        'XMDM': XMDM, 'YYRQ': YYRQ, 'YYLX': YYLX, 'KSSJ': KSSJ, 'JSSJ': JSSJ, 'XQDM': XQDM}, "获取场地列表")
    try:
        rows = ret["datas"]["getOpeningRoom"]["rows"] if ret else None
        if not isinstance(rows, list):
            logger.error("获取场地列表失败: 响应缺少 rows")
            return None
        logger.info("获取场地列表成功: %d 个场地", len(rows))
        return rows
    except (KeyError, TypeError):
        logger.error("获取场地列表失败: 响应结构异常")
        return None


def postBook(CGDM, CDWID, XMDM, XQWID, KYYSJD, YYRQ, YYLX):
    if not all(str(v).strip() for v in (CGDM, CDWID, XMDM, XQWID, KYYSJD, YYRQ, YYLX, stuid, stuname)):
        logger.error("预约失败: 参数不能为空")
        return None
    try:
        start, end = [part.strip() for part in str(KYYSJD).split("-", 1)]
        if not start or not end:
            raise ValueError
    except ValueError:
        logger.error("预约失败: 时间段格式无效，应为 HH:MM-HH:MM")
        return None
    data = {'DHID': '', 'CYRS': '', 'YYRGH': stuid, 'YYRXM': stuname, 'CGDM': CGDM,
            'CDWID': CDWID, 'XMDM': XMDM, 'XQWID': XQWID, 'KYYSJD': KYYSJD,
            'YYRQ': YYRQ, 'YYLX': YYLX, 'YYKS': f"{YYRQ} {start}",
            'YYJS': f"{YYRQ} {end}", 'PC_OR_PHONE': 'pc'}
    ret = _post_json("https://ehall.szu.edu.cn/qljfwapp/sys/lwSzuCgyy/sportVenue/insertVenueBookingInfo.do", data, "预约场地")
    if ret is not None and not isinstance(ret, dict):
        logger.error("预约场地失败: JSON 根节点不是对象")
        return None
    return ret
