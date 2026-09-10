#!/usr/bin/env python3
"""Interactive venue booking wizard.

The wizard reads only identity fields from user.yaml and asks for the current
ehall cookie at runtime.  It intentionally never writes the cookie to disk.
"""
import getpass
import re
import time
from datetime import date as date_type, timedelta
from pathlib import Path

import apis


def read_identity(path="user.yaml"):
    data = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(stuid|stuname)\s*:\s*[\"']?(.*?)[\"']?\s*$", line)
        if m:
            data[m.group(1)] = m.group(2).strip()
    if not data.get("stuid") or not data.get("stuname"):
        raise ValueError(f"{path} 需要包含 stuid 和 stuname 字段")
    return data


def cookie_dict(raw):
    return {x.strip().split("=", 1)[0]: x.strip().split("=", 1)[1]
            for x in raw.split(";") if "=" in x}


def rows_from(ret):
    if isinstance(ret, dict):
        d = ret.get("datas", ret)
        if isinstance(d, dict):
            for v in d.values():
                if isinstance(v, list): return v
    return ret if isinstance(ret, list) else []


def choose(items, title):
    print(f"\n{title}")
    for i, x in enumerate(items, 1): print(f"  {i:>2}. {x}")
    while True:
        try:
            n = int(input("请输入序号: "))
            if 1 <= n <= len(items): return items[n - 1]
        except ValueError: pass
        print("序号无效，请重试")


def main():
    identity = read_identity()
    apis.stuid, apis.stuname = identity["stuid"], identity["stuname"]
    apis.cookies = cookie_dict(getpass.getpass("请输入 ehall cookies（隐藏输入）: "))
    config = apis.getSysConfig()
    if not config: raise RuntimeError("无法获取场馆列表，请检查 cookies 是否过期")
    venues = []
    for kind, key, typ in [("包场", "packageVenueList", "1.0"), ("散场", "dismissalVenueList", "2.0")]:
        for v in config.get(key, []):
            venues.append({"name": v.get("CGMC", ""), "activity": v.get("XM"),
                           "venue": v.get("CGBM"), "campus": v.get("SSXQ"), "type": typ, "kind": kind})
    venue_labels = [f"{v['name']}｜{v['kind']}｜校区{v['campus']}｜项目{v['activity']}｜场馆{v['venue']}" for v in venues]
    venue = venues[venue_labels.index(choose(venue_labels, "可预约场馆"))]
    print(f"\n已选择：{venue['name']}（{venue['kind']}，项目代码 {venue['activity']}）")
    # 学校系统每天 12:30 开放次日预约，因此只查询今天和明天。
    print("\n正在查询今天和明天的日期/时段…")
    available_by_date = {}
    for n in range(2):
        d = (date_type.today() + timedelta(days=n)).isoformat()
        times = rows_from(apis.getTimeList(venue["campus"], d, venue["type"], venue["activity"]))
        if times: available_by_date[d] = times
    if not available_by_date:
        raise RuntimeError("今天和明天没有可查询的预约日期")
    date = choose(list(available_by_date), "可预约日期")
    times = available_by_date[date]
    print(f"\n{date} 的预约时段")
    time_labels = []
    for row in times:
        code = row.get("CODE", row.get("NAME", "未知时段")) if isinstance(row, dict) else str(row)
        status = "可预约" if isinstance(row, dict) and not row.get("disabled") else (row.get("text", "不可用") if isinstance(row, dict) else "不可用")
        time_labels.append(f"{code}｜{status}")
    selected_time = choose(time_labels, "请选择预约时段")
    time_index = time_labels.index(selected_time)
    period = times[time_index].get("CODE", times[time_index].get("NAME", ""))
    if not re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", period):
        raise ValueError("接口返回的时段格式无效")
    course = {"CGDM": venue["venue"], "XMDM": venue["activity"], "XQWID": venue["campus"],
              "KYYSJD": period, "YYRQ": date, "YYLX": venue["type"]}
    mode = input("运行模式：1执行一次，2持续轮询直到成功（默认2）: ").strip() or "2"
    delay = int(input("轮询间隔毫秒（默认1000）: ").strip() or "1000")
    while True:
        start, end = period.split("-", 1)
        rooms = apis.getRoom(XMDM=venue["activity"], YYRQ=date, YYLX=venue["type"],
                             KSSJ=start, JSSJ=end, XQDM=venue["campus"])
        available = [r for r in rooms or [] if not r.get("disabled") and r.get("CGBM") == venue["venue"]]
        if available:
            for room in available:
                ret = apis.postBook(CDWID=room["WID"], **course)
                print(ret)
                if isinstance(ret, dict) and str(ret.get("code")) == "0": return
        elif mode != "2":
            print("当前无可预约场地"); return
        print("当前无空位，继续轮询…")
        time.sleep(delay / 1000)


if __name__ == "__main__": main()
