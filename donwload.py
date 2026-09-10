#!/usr/bin/python3
# -*- coding: utf-8 -*-
# @File    : getData.py
import os

import pandas as pd

from apis import getSysConfig, getTimeList, getRoom


def downloadSysConfig():
    config = getSysConfig()
    if config is None:
        print("获取系统配置失败")
        exit(1)
    venues = []
    for v in config["packageVenueList"]:
        venues.append({
            "WID": v["WID"],
            "SSXQ": v["SSXQ"],
            "XM": v["XM"],
            "CGBM": v["CGBM"],
            "CGMC": v["CGMC"],
            "DCFS": "1.0",
        })
    for v in config["dismissalVenueList"]:
        venues.append({
            "WID": v["WID"],
            "SSXQ": v["SSXQ"],
            "XM": v["XM"],
            "CGBM": v["CGBM"],
            "CGMC": v["CGMC"],
            "DCFS": "2.0",
        })
    activities = []
    for xm in config["xmList"]:
        activities.append({
            "XMDM": xm["XMDM"],
            "XMMC": xm["XMMC"],
            "DCFS": xm["DCFS"],
            "XQDM": xm["XQDM"],
        })
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    pd.DataFrame(venues).to_excel(os.path.join(os.path.dirname(__file__), "data", "venues.xlsx"), index=False)
    pd.DataFrame(activities).to_excel(os.path.join(os.path.dirname(__file__), "data", "activities.xlsx"), index=False)
    print("获取数据成功")


def downloadTimeList(XQ, YYRQ, YYLX, XMDM):
    """
    获取时间列表
    :param XQ: 校区(代码)
    :param YYRQ: 预约日期 例如 2025-01-01
    :param YYLX: 预约类型 即订场方式(1.0: 包场, 2.0: 散场 )
    :param XMDM: 项目代码 例如 001
    :return:
    """
    ret = getTimeList(XQ, YYRQ, YYLX, XMDM)
    if ret is None:
        print("获取时间列表失败")
        exit(1)
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    filename = "TimeList" + "_".join([YYRQ, YYLX, XMDM, XQ]) + ".xlsx"
    pd.DataFrame(ret).to_excel(os.path.join(os.path.dirname(__file__), "data", filename), index=False)


def downloadRoom(XMDM, YYRQ, YYLX, KSSJ, JSSJ, XQDM):
    """
    获取场地列表
    :param XMDM: 项目代码 例如 001
    :param YYRQ: 预约日期 例如 2025-01-01
    :param YYLX: 预约类型 即订场方式(1.0: 包场, 2.0: 散场 )
    :param KSSJ: 开始时间 例如 08:00
    :param JSSJ: 结束时间 例如 09:00
    :param XQDM: 校区代码(1:粤海, 2:丽湖)
    :param CGBM: 场馆编码
    :return:
    """
    ret = getRoom(XMDM, YYRQ, YYLX, KSSJ, JSSJ, XQDM)
    if ret is None:
        print("获取场地列表失败")
        exit(1)
    for room in ret:
        room["CDWID"] = room["WID"]
        del room["WID"]
    os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)
    filename = "RoomList" + "_".join([YYRQ, YYLX, XMDM]) + ".xlsx"
    pd.DataFrame(ret).to_excel(os.path.join(os.path.dirname(__file__), "data", filename), index=False)


if __name__ == '__main__':
    downloadSysConfig()
    # 请修改下面的参数, 以查询需要的场地
    # downloadTimeList("1", "2025-05-01", "1.0", "001")
    downloadRoom("001", "2025-05-01", "1.0", "20:00", "21:00", "1")