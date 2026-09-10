
import logging
import time
import copy  # 添加深拷贝支持
import argparse
import getpass
import json
from apis import postBook, getRoom
import settings
import apis

courses = settings.courses
delay = settings.delay
counts = settings.counts

logger = logging.getLogger(__name__)
CDWIDs = []
datas = []


def is_success_response(response):
    if not isinstance(response, dict):
        return False
    return response.get("code") in {"0", 0} or "成功" in str(response)


def is_terminal_failure(response):
    if not isinstance(response, dict):
        return False

    msg = str(response.get("msg", ""))
    terminal_markers = [
        "只能预订2次",
        "已预订2次",
        "黑名单",
        "无预约资格",
        "不可预约",
    ]
    return any(marker in msg for marker in terminal_markers)


def resolve_rooms(course):
    rooms = getRoom(**{
        "XMDM": course["XMDM"],
        "YYRQ": course["YYRQ"],
        "YYLX": course["YYLX"],
        "KSSJ": course["KYYSJD"].split("-")[0],
        "JSSJ": course["KYYSJD"].split("-")[1],
        "XQDM": course["XQWID"],
    })
    time.sleep(0.2)
    if rooms is None:
        logger.error(f"获取场地失败: {course}")
        return None

    available_courses = []
    for room in rooms:
        # getOpeningRoom may return both ordinary and staff-only badminton courts;
        # honor the requested venue code so ordinary bookings never spill over.
        if room.get("CGBM") != course.get("CGDM"):
            continue
        if not room["disabled"]:
            course_copy = copy.deepcopy(course)
            course_copy["CDWID"] = room["WID"]
            available_courses.append(course_copy)
    return available_courses


def prompt_run_mode():
    print("请选择运行模式:")
    print("1. 按当前设置执行")
    print("2. 一直抢直到抢到为止")

    while True:
        mode = input("请输入模式编号 (1/2，默认 1): ").strip() or "1"
        if mode in {"1", "2"}:
            break
        print("输入无效，请输入 1 或 2")

    current_delay = delay
    while True:
        delay_input = input(f"请输入轮询延迟毫秒数 (默认 {delay}): ").strip()
        if not delay_input:
            break
        if delay_input.isdigit() and int(delay_input) >= 0:
            current_delay = int(delay_input)
            break
        print("输入无效，请输入大于等于 0 的整数")

    current_counts = counts
    if mode == "1":
        while True:
            counts_input = input(f"请输入执行轮次 (默认 {counts}): ").strip()
            if not counts_input:
                break
            if counts_input.isdigit() and int(counts_input) > 0:
                current_counts = int(counts_input)
                break
            print("输入无效，请输入大于 0 的整数")

    return mode, current_delay, current_counts


def parse_args():
    parser = argparse.ArgumentParser(description="深圳大学体育场馆预约助手")
    parser.add_argument("--stuid", help="学号（默认读取 settings.py）")
    parser.add_argument("--stuname", help="姓名（默认读取 settings.py）")
    parser.add_argument("--cookies", help="登录 cookies；不建议直接写在 shell 历史中")
    parser.add_argument("--cookies-file", help="从文件读取 cookies")
    parser.add_argument("--cookies-prompt", action="store_true", help="启动时隐藏输入 cookies")
    parser.add_argument("--date", dest="date", help="预约日期，例如 2026-09-03")
    parser.add_argument("--time", dest="time", help="预约时段，例如 16:00-17:00")
    parser.add_argument("--venue", dest="venue", help="场馆代码 CGDM，例如 004")
    parser.add_argument("--activity", dest="activity", help="项目代码 XMDM，例如 007")
    parser.add_argument("--campus", default="1", help="校区代码，1粤海/2丽湖")
    parser.add_argument("--type", dest="book_type", default="2.0", help="预约类型，1.0包场/2.0散场")
    parser.add_argument("--room", help="场地 ID（可选；不填则自动选择可用场地）")
    parser.add_argument("--delay", type=int, help="轮询间隔，毫秒")
    parser.add_argument("--counts", type=int, help="普通模式执行轮次")
    parser.add_argument("--mode", choices=["1", "2"], help="1按轮次，2持续抢到成功")
    parser.add_argument("--course-json", help="直接传入预约记录 JSON 数组，优先级最高")
    return parser.parse_args()


def apply_cli_config(args):
    global courses, delay, counts
    if args.stuid:
        apis.stuid = settings.stuid = args.stuid
    if args.stuname:
        apis.stuname = settings.stuname = args.stuname
    if args.cookies_file:
        with open(args.cookies_file, encoding="utf-8") as f:
            settings.cookies = f.read().strip()
    elif args.cookies_prompt:
        settings.cookies = getpass.getpass("请输入 cookies（隐藏输入）: ")
    elif args.cookies:
        settings.cookies = args.cookies
    if isinstance(settings.cookies, str):
        settings.cookies = dict(item.strip().split("=", 1) for item in settings.cookies.split(";") if "=" in item)
    apis.cookies = settings.cookies
    if args.course_json:
        courses = json.loads(args.course_json)
    elif any([args.date, args.time, args.venue, args.activity, args.room]):
        base = dict(courses[0]) if courses else {}
        if args.date: base["YYRQ"] = args.date
        if args.time: base["KYYSJD"] = args.time
        if args.venue: base["CGDM"] = args.venue
        if args.activity: base["XMDM"] = args.activity
        if args.campus: base["XQWID"] = args.campus
        if args.book_type: base["YYLX"] = args.book_type
        if args.room: base["CDWID"] = args.room
        courses = [base]
    if args.delay is not None: delay = args.delay
    if args.counts is not None: counts = args.counts


if __name__ == '__main__':
    args = parse_args()
    apply_cli_config(args)
    if args.mode:
        mode = args.mode
        current_delay = delay
        current_counts = counts
    else:
        mode, current_delay, current_counts = prompt_run_mode()
    while len(courses):
        course = courses[0]
        if course.get("CDWID", None) is None:
            available_courses = resolve_rooms(course)
            if available_courses is None:
                datas.append(copy.deepcopy(course))
            elif available_courses:
                datas.extend(available_courses)
            else:
                logger.error(f"没有可预约的场地: {course}")
                print(f"没有可预约的场地: {course}")
                datas.append(copy.deepcopy(course))
        else:
            datas.append(copy.deepcopy(course))
        courses.pop(0)

    round_index = 0
    while datas and (mode == "2" or round_index < current_counts):
        round_index += 1
        i = 0
        while i < len(datas):
            course = datas[i]
            try:
                if course.get("CDWID", None) is None:
                    available_courses = resolve_rooms(course)
                    if available_courses is None:
                        time.sleep(current_delay / 1000)
                        i += 1
                        continue
                    if not available_courses:
                        logger.info(f"当前仍无可预约场地，继续等待: {course}")
                        time.sleep(current_delay / 1000)
                        i += 1
                        continue
                    datas.pop(i)
                    for available_course in reversed(available_courses):
                        datas.insert(i, available_course)
                    continue

                logger.info(f"开始预约: {course}")
                ret = postBook(**course)
                if ret is None:
                    time.sleep(current_delay / 1000)
                    i += 1
                    continue
                if is_success_response(ret):
                    logger.info(f"预约成功: {course}")
                    print(f"预约成功: {course}")
                    datas = [
                        item for item in datas 
                        if item["KYYSJD"] != course["KYYSJD"] or item["YYRQ"] != course["YYRQ"]
                    ]
                    i = 0
                    continue
                if is_terminal_failure(ret):
                    logger.error(f"预约终止: {ret.get('msg', ret)}")
                    print(f"预约终止: {ret.get('msg', ret)}")
                    datas = [
                        item for item in datas
                        if not (
                            item["YYRQ"] == course["YYRQ"]
                            and item["XMDM"] == course["XMDM"]
                            and item["XQWID"] == course["XQWID"]
                            and item["YYLX"] == course["YYLX"]
                        )
                    ]
                    i = 0
                    continue
                time.sleep(current_delay / 1000)
            except Exception as e:
                logger.error(f"预约失败: {e}")
            i += 1
