"""Streamlit web UI for the venue booking assistant.

Run with: ``streamlit run app.py``
Cookies are entered at runtime and are never persisted by this module.
"""
from __future__ import annotations

import os
import sys
import re
import time
import json
import threading
import uuid
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import streamlit as st

import apis


def app_home() -> Path:
    """Writable directory next to the exe, or the source tree during development."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


HOME = app_home()
LOG_PATH = HOME / "OPERATION_LOG.md"
PROFILE_PATH = HOME / ".venue_profile.json"
@st.cache_resource
def job_registry():
    """Retain background jobs across Streamlit script reruns."""
    return {}, threading.Lock()


JOBS, JOBS_LOCK = job_registry()


def load_profile() -> dict[str, str]:
    """Load non-sensitive identity fields saved locally for convenience."""
    try:
        data = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {key: str(data.get(key, "")).strip() for key in ("stuid", "stuname")}
    except (OSError, json.JSONDecodeError):
        pass
    return {"stuid": str(getattr(apis, "stuid", "")), "stuname": str(getattr(apis, "stuname", ""))}


def save_profile(stuid: str, stuname: str) -> None:
    """Persist only name and student ID; never persist cookies."""
    try:
        PROFILE_PATH.write_text(
            json.dumps({"stuid": stuid, "stuname": stuname}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def op_log(message: str, level: str = "INFO") -> None:
    """Write an operation event to the internal session state and log file."""
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] [{level}] {message}"
    st.session_state.setdefault("op_logs", []).append(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def cookie_dict(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in (raw or "").split(";"):
        if "=" in item:
            key, value = item.strip().split("=", 1)
            if key:
                result[key.strip()] = value.strip()
    return result


def rows_from(ret: Any) -> list[Any]:
    if isinstance(ret, list):
        return ret
    if isinstance(ret, dict):
        data = ret.get("datas", ret)
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list):
                    return value
    return []


def parse_time_list(ret: Any) -> tuple[list[Any] | None, str | None]:
    """Return (rows, error). rows is None when the query itself failed."""
    if ret is None:
        return None, "查询失败，请检查网络或 Cookie 是否过期后重试。"
    rows = rows_from(ret)
    if not rows and isinstance(ret, dict):
        code = ret.get("code")
        if code not in {None, 0, "0"}:
            msg = str(ret.get("msg") or "查询失败").strip()
            return None, f"查询失败：{msg}"
    return rows, None


def slot_options(times: list[Any]) -> tuple[dict[str, str], list[str]]:
    """Split time rows into bookable labels and unavailable captions."""
    available: dict[str, str] = {}
    unavailable: list[str] = []
    for row in times:
        if not isinstance(row, dict):
            continue
        code = str(row.get("CODE", row.get("NAME", "")))
        if not re.fullmatch(r"\d{2}:\d{2}-\d{2}:\d{2}", code):
            continue
        if row.get("disabled", False):
            reason = str(row.get("text") or row.get("STATE_EXPLAIN") or "不可预约")
            unavailable.append(f"{code}（{reason}）")
        else:
            available[f"{code}（可预约）"] = code
    return available, unavailable


def is_success(response: Any) -> bool:
    return isinstance(response, dict) and response.get("code") in {0, "0"}


def is_terminal(response: Any) -> bool:
    if not isinstance(response, dict):
        return False
    msg = str(response.get("msg", response))
    return any(x in msg for x in (
        "只能预订2次",
        "已预订2次",
        "黑名单",
        "无预约资格",
        "不可预约",
        "预约人学工号不是当前登录人",
        "学工号不是当前登录人",
    ))


def venue_options(config: dict[str, Any]) -> list[dict[str, str]]:
    options = []
    for key, typ, kind in (("packageVenueList", "1.0", "包场"), ("dismissalVenueList", "2.0", "散场")):
        for venue in config.get(key, []) or []:
            options.append({
                "name": venue.get("CGMC", "未命名场馆"),
                "activity": str(venue.get("XM", venue.get("XMDM", ""))),
                "activity_name": str(venue.get("XMMC", venue.get("XM", ""))),
                "venue": str(venue.get("CGBM", "")),
                "campus": str(venue.get("SSXQ", venue.get("XQDM", "1"))),
                "type": typ,
                "kind": kind,
            })
    return [v for v in options if v["venue"] and v["activity"]]


def available_rooms(course: dict[str, str]) -> list[dict[str, Any]] | None:
    start, end = course["KYYSJD"].split("-", 1)
    rooms = apis.getRoom(course["XMDM"], course["YYRQ"], course["YYLX"], start, end, course["XQWID"])
    if rooms is None:
        return None
    return [r for r in rooms if isinstance(r, dict) and not r.get("disabled", False)
            and str(r.get("CGBM", "")) == course["CGDM"]]


def job_log(job: dict[str, Any], message: str, level: str = "INFO") -> None:
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] [{level}] {message}"
    with JOBS_LOCK:
        job["logs"].append(line)
    try:
        with LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def booking_worker(job_id: str, course: dict[str, str], infinite: bool, rounds: int, delay_ms: int) -> None:
    with JOBS_LOCK:
        job = JOBS[job_id]
    attempt = 0
    try:
        while infinite or attempt < rounds:
            if job["stop_event"].is_set():
                job_log(job, f"已手动停止预约（完成 {attempt} 轮）", "WARNING")
                break
            attempt += 1
            with JOBS_LOCK:
                job["attempt"] = attempt
                job["status"] = "running"
                job["detail"] = "正在查询可用场地…"
            rooms = available_rooms(course)
            if rooms is None:
                job_log(job, f"第 {attempt} 轮获取场地失败", "ERROR")
                with JOBS_LOCK: job["detail"] = "接口暂时未返回场地，稍后重试…"
            elif not rooms:
                job_log(job, f"第 {attempt} 轮暂无空闲场地")
                with JOBS_LOCK: job["detail"] = "当前暂无空闲场地，等待下一轮…"
            else:
                with JOBS_LOCK: job["detail"] = f"发现 {len(rooms)} 个可预约场地，正在提交预约…"
                for room in rooms:
                    if job["stop_event"].is_set(): break
                    ret = apis.postBook(CDWID=room.get("WID"), **course)
                    if is_success(ret):
                        job_log(job, f"预约成功，场地 {room.get('WID')}，第 {attempt} 轮", "SUCCESS")
                        with JOBS_LOCK:
                            job.update(status="success", success=True, detail=f"预约成功，场地 {room.get('WID')}")
                        return
                    if is_terminal(ret):
                        job_log(job, f"预约终止：{ret}", "ERROR")
                        message = str(ret.get("msg", "预约被系统终止"))
                        if "学工号不是当前登录人" in message:
                            message = (
                                "系统未通过预约人身份校验：请确认 Cookie 仍有效、账号已登录，"
                                "且预约学号格式与学校系统登记一致后重新连接。"
                            )
                        with JOBS_LOCK: job.update(status="terminal", detail=message)
                        return
                    job_log(job, f"场地 {room.get('WID')} 预约失败：{ret}", "WARNING")
            if not infinite and attempt >= rounds: break
            job["stop_event"].wait(delay_ms / 1000)
        with JOBS_LOCK:
            job.update(status="stopped" if job["stop_event"].is_set() else "finished", detail=f"已完成 {attempt} 轮，未预约成功")
    except Exception as exc:
        job_log(job, f"预约任务异常：{exc}", "ERROR")
        with JOBS_LOCK: job.update(status="error", detail="预约任务异常，请稍后重试")


@st.fragment(run_every="1s")
def render_booking_job(job_id: str) -> None:
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        snapshot = dict(job) if job else None
    if not snapshot:
        return
    if snapshot["status"] == "running":
        st.info(f"预约进行中：第 {snapshot['attempt']} 轮")
        st.caption(snapshot["detail"])
        if st.button("停止预约", key=f"stop-{job_id}"):
            job["stop_event"].set()
            with JOBS_LOCK:
                job["detail"] = "正在停止预约，请等待当前请求结束…"
            st.warning("已请求停止，当前网络请求结束后停止轮询")
    elif snapshot["status"] == "success":
        st.success(snapshot["detail"] or "预约成功")
        # Fragment and full-page reruns must not repeat the success toast.
        should_notify = False
        with JOBS_LOCK:
            if not job.get("success_notified", False):
                job["success_notified"] = True
                should_notify = True
        if should_notify:
            st.toast("预约成功！", icon="✅")
    elif snapshot["status"] in {"terminal", "error"}:
        st.error(snapshot["detail"])
    else:
        st.warning(snapshot["detail"])


def main() -> None:
    st.set_page_config(
        page_title="深大场馆预约",
        page_icon="🏟️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.cn/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Sans:wght@400;500;600;700&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,500;0,6..72,600;1,6..72,400&display=swap');

        :root {
          --background: #FAF9F5; --surface1: #F0EEE6; --surface2: #E8E6DC;
          --surface3: #E3DACC; --border: #D1CFC5; --text1: #141413;
          --text2: #3D3D3A; --text3: #5E5D59; --text4: #87867F;
          --accent: #D97757; --accent-subtle: #F0EEE6; --success: #788C5D;
          --font-display: 'Newsreader', Georgia, serif;
          --font-body: 'Instrument Sans', system-ui, sans-serif;
          --font-mono: 'IBM Plex Mono', ui-monospace, monospace;
        }
        @media (prefers-color-scheme: dark) {
          :root { --background:#141413; --surface1:#1A1918; --surface2:#3D3D3A; --surface3:#5E5D59; --border:#3D3D3A; --text1:#FAF9F5; --text2:#E8E6DC; --text3:#B0AEA5; --text4:#87867F; --accent:#DE9274; --accent-subtle:#1A1918; --success:#788C5D; }
          .stApp, [data-testid="stAppViewContainer"] { background:var(--background); color:var(--text1); }
          [data-testid="stHeader"] { background:rgba(20,20,19,.92); }
          [data-testid="stSidebar"] { background:var(--surface1); }
          .evidence-note { border-color:var(--border); background:var(--surface1); }
          .evidence-note strong { color:var(--text4); }
        }
        html, body, [class*="css"] { font-family: var(--font-body); }
        .stApp { background: var(--background); color: var(--text1); }
        [data-testid="stAppViewContainer"] { background: var(--background); }
        [data-testid="stHeader"] {
          background: rgba(250,249,245,.96);
          border-bottom: 1px solid var(--border);
          height: 68px;
        }
        [data-testid="stDecoration"],
        [data-testid="stAppDeployButton"],
        [data-testid="stMainMenu"],
        [data-testid="stToolbarActions"] { display: none !important; }
        [data-testid="stExpandSidebarButton"] { display: flex !important; }
        .app-topline {
          position: fixed;
          top: 0;
          left: 3.25rem;
          right: 0;
          height: 68px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 2rem 0 .55rem;
          pointer-events: none;
          z-index: 999990;
        }
        body:has(.login-intro) .app-topline {
          left: 0;
          padding-left: 2rem;
        }
        [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][aria-expanded="true"]) .app-topline {
          left: 21rem;
          padding-left: 1.5rem;
        }
        .app-topline .brandmark {
          font-family: var(--font-body);
          font-size: 1.05rem;
          font-weight: 600;
          letter-spacing: -.01em;
          color: var(--text1);
          white-space: nowrap;
        }
        .app-topline .brandmark span { color: var(--text1); margin-right: .55rem; font-size: .7rem; }
        .app-topline .topmeta {
          font: 400 .72rem/1.2 var(--font-display);
          letter-spacing: .02em;
          text-transform: none;
          color: var(--text3);
          white-space: nowrap;
          margin-left: auto;
        }
        @media (max-width: 760px) {
          .app-topline { padding-right: 1rem; }
          body:has(.login-intro) .app-topline { padding-left: 1rem; }
          .app-topline .topmeta { display: none; }
        }
        [data-testid="stSidebar"] { background: var(--surface1); border-right: 1px solid var(--border); }
        [data-testid="stSidebar"] > div:first-child { padding: 2rem 1.35rem; }
        body:has(.login-intro) [data-testid="stSidebar"] { display: none; }
        body:has(.login-intro) [data-testid="stMainBlockContainer"] { max-width:720px; padding-top:6.5rem; padding-bottom:3rem; }
        body:has(.login-intro) .evidence-note { margin-top:1.5rem; }
        .section-intro.login-intro { border-top:0; padding-top:.25rem; margin:0 0 1.75rem; }
        [data-testid="stForm"] { background:transparent; border:1px solid var(--border); border-radius:8px; padding:28px; }
        [data-testid="stForm"] [data-testid="stTextInputRootElement"] { background:var(--background); border:1px solid var(--border); border-radius:8px; }
        [data-testid="stForm"] input { background:transparent; color:var(--text1); }
        [data-testid="stForm"] [data-testid="stWidgetLabel"] p { color:var(--text2); font-family:var(--font-body); }
        [data-testid="stFormSubmitButton"] { width:100% !important; display:block; }
        [data-testid="stFormSubmitButton"] button { width:100% !important; min-height:44px; border-radius:999px; background:var(--text1); color:var(--background); border:1px solid var(--text1); font-weight:600; }
        [data-testid="stFormSubmitButton"] button:hover { background:var(--text2); border-color:var(--text2); }
        [data-testid="stFormSubmitButton"] button p { color:inherit; }
        [data-testid="stSidebar"] h2 { font-family: var(--font-display); font-size: 1.85rem; font-weight: 400; letter-spacing: -.03em; color: var(--text1); }
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color: var(--text3); }
        [data-testid="stSidebar"] [data-testid="stButton"] p { color: inherit !important; }
        [data-testid="stSidebar"] [data-testid="stTextInput"] input { background: var(--background); }
        .page-shell { max-width: 1040px; margin: 0 auto; padding: 1.8rem 2.5rem 2.5rem; }
        .brandmark { font-family:var(--font-body); font-size:1.05rem; color:var(--text1); letter-spacing:-.01em; }
        .brandmark span { color:var(--text1); }
        .hero { max-width: 760px; margin-bottom: 2.1rem; }
        .eyebrow, .section-kicker, p.section-kicker { font:400 .68rem/1.35 var(--font-mono); text-transform:uppercase; letter-spacing:.12em; color:var(--text4) !important; margin:0 0 1rem; }
        .section-intro [data-testid="stHeaderActionElements"] { display:none; }
        .section-intro [data-testid="stHeadingWithActionElements"] h2, .section-intro h2 { padding:0 !important; }
        .hero p { max-width: 58ch; font-size:1.05rem; line-height:1.65; color:var(--text3); margin:0; }
        .context-strip { display:flex; align-items:center; gap:.7rem; margin-top:1.6rem; font:400 .7rem var(--font-mono); color:var(--text4); }
        .status-dot { width:7px; height:7px; border-radius:50%; background:var(--text1); display:inline-block; }
        .section-intro { padding-top:2.2rem; margin:1.4rem 0 1.5rem; }
        .section-intro h2 { font:400 2.6rem/1.08 var(--font-display); letter-spacing:-.035em; margin:0; color:var(--text1); }
        .section-intro p { max-width:62ch; color:var(--text3); font-size:1.02rem; margin:.7rem 0 0; line-height:1.6; }
        [data-testid="stVerticalBlock"]:has(.section-intro) { gap: .5rem; }
        [data-testid="stSelectbox"] > div, [data-testid="stDateInput"] > div { border-radius:8px; }
        [data-testid="stSelectbox"] label, [data-testid="stDateInput"] label, [data-testid="stRadio"] label, [data-testid="stNumberInput"] label { font:400 .68rem var(--font-mono); letter-spacing:.08em; text-transform:uppercase; color:var(--text4); }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div, [data-testid="stDateInput"] input, [data-testid="stNumberInput"] input { background:var(--background); border-color:var(--border); }
        [data-testid="stButton"] button { border-radius:999px; min-height:44px; font-weight:600; transition:all .16s ease; padding:0 1.25rem; }
        [data-testid="stButton"] button[kind="primary"] { background:var(--text1); border-color:var(--text1); color:var(--background); }
        [data-testid="stButton"] button[kind="primary"]:hover { background:var(--text2); border-color:var(--text2); color:var(--background); }
        [data-testid="stButton"] button[kind="primary"] p { color:inherit !important; }
        [data-testid="stButton"] button:not([kind="primary"]) { border-color:var(--text1); color:var(--background); background:var(--text1); }
        [data-testid="stButton"] button:not([kind="primary"]):hover { background:var(--text2); border-color:var(--text2); color:var(--background); }
        [data-testid="stButton"] button:not([kind="primary"]) p { color:inherit !important; }
        [data-testid="stButton"] button:disabled,
        [data-testid="stButton"] button[disabled] { opacity:.45; }
        [data-testid="stAlert"] { border-radius:8px; border:1px solid var(--border); background:var(--surface1); }
        [data-testid="stMetricValue"] { font-family:var(--font-mono); }
        .evidence-note { margin-top:3rem; padding:1.25rem 1.4rem; border:1px solid var(--border); border-radius:8px; background:var(--surface1); color:var(--text2); font:400 .9rem/1.6 var(--font-display); }
        .evidence-note strong { font:400 .68rem var(--font-mono); letter-spacing:.12em; text-transform:uppercase; color:var(--text4); display:block; margin-bottom:.4rem; }
        @media (max-width: 760px) { .page-shell { padding:1.3rem 1rem 3rem; } }
        </style>
        <div id="app-topline" class="app-topline"><div class="brandmark"><span>●</span>深大场馆预约</div><div class="topmeta">SHENZHEN UNIVERSITY · RESERVATIONS</div></div>
        """,
        unsafe_allow_html=True,
    )

    active_job = st.session_state.get("booking_job_id")
    with JOBS_LOCK:
        job_running = bool(active_job and JOBS.get(active_job, {}).get("status") == "running")

    connected = bool(st.session_state.get("connected", False))
    if connected:
        with st.sidebar:
            st.markdown('<p class="section-kicker">Session / 01</p>', unsafe_allow_html=True)
            st.header("已连接")
            profile = st.session_state.get("profile", {})
            st.caption(f"{profile.get('stuname', '')} · {profile.get('stuid', '')}")
            st.caption("预约进行中，请先停止任务再退出。" if job_running else "登录成功，可以开始预约。")
            if st.button("退出当前会话", disabled=job_running):
                st.session_state["connected"] = False
                for key in ("venues", "times", "time_map", "time_query_key", "times_error", "booking_job_id", "cookie_input"):
                    st.session_state.pop(key, None)
                apis.cookies = {}
                apis._session.cookies.clear()
                st.rerun()
    else:
        st.markdown('<div class="section-intro login-intro"><p class="section-kicker">Access / 01</p><h2>登录场馆预约</h2><p>填写姓名、学号和有效的 ehall Cookie，登录后进入预约工作区。</p></div>', unsafe_allow_html=True)
        profile = st.session_state.setdefault("profile", load_profile())
        with st.form("login_form"):
            login_cols = st.columns(2, gap="large")
            with login_cols[0]:
                stuid = st.text_input("学号", value=profile.get("stuid", ""), key="stuid_input")
            with login_cols[1]:
                stuname = st.text_input("姓名", value=profile.get("stuname", ""), key="stuname_input")
            raw_cookie = st.text_input(
                "ehall Cookie",
                type="password",
                key="cookie_input",
                help="从浏览器开发者工具复制 Cookie 请求头内容；仅在当前会话使用",
            )
            if st.form_submit_button("登录并进入预约", type="primary", use_container_width=True):
                if not stuid.strip() or not stuname.strip() or not cookie_dict(raw_cookie):
                    st.error("请填写学号、姓名和 Cookie")
                else:
                    apis.stuid, apis.stuname = stuid.strip(), stuname.strip()
                    apis.cookies = cookie_dict(raw_cookie)
                    op_log("开始加载场馆配置")
                    with st.spinner("正在验证登录并加载场馆…"):
                        config = apis.getSysConfig()
                    if isinstance(config, dict) and any(
                        isinstance(config.get(key), list)
                        for key in ("packageVenueList", "dismissalVenueList")
                    ):
                        st.session_state["venues"] = venue_options(config)
                        st.session_state["connected"] = True
                        save_profile(apis.stuid, apis.stuname)
                        st.session_state["profile"] = {"stuid": apis.stuid, "stuname": apis.stuname}
                        op_log(f"场馆配置加载成功，共 {len(st.session_state['venues'])} 项")
                        st.rerun()
                    else:
                        apis.cookies = {}
                        apis._session.cookies.clear()
                        st.error("加载失败，请检查 Cookie 是否过期")
                        op_log("场馆配置加载失败", "ERROR")

        st.markdown('<div class="evidence-note"><strong>Privacy note</strong>姓名与学号仅保存在本机的便捷配置中；Cookie 仅用于当前会话的接口请求。</div>', unsafe_allow_html=True)
        return

    # Keep stop controls available after login, even when no times are loaded.
    if active_job:
        render_booking_job(active_job)

    all_venues = st.session_state.get("venues", [])
    if not all_venues:
        st.markdown('<div class="section-intro"><p class="section-kicker">Workspace / 02</p><h2>场馆预约</h2></div>', unsafe_allow_html=True)
        st.info("登录成功，当前暂无可预约场馆。可稍后退出并重新登录以加载场馆。")
    else:
        st.markdown('<div class="section-intro"><p class="section-kicker">Workspace / 02</p><h2>选择你的运动时段。</h2><p>按校区、场馆和日期逐步缩小范围，再查询可预约的时间段。</p></div>', unsafe_allow_html=True)
        control_cols = st.columns([1, 2], gap="large")
        with control_cols[0]:
            campus = st.selectbox("选择校区", ["1", "2"], format_func=lambda x: {
                "1": "粤海校区",
                "2": "丽湖校区",
            }[x])
        venues = [v for v in all_venues if v.get("campus") == campus]
        if not venues:
            st.warning("该校区暂无可预约场馆")
        else:
            labels = [f"{v['name']}｜{v['kind']}｜{v['activity_name'] or v['activity']}" for v in venues]
            with control_cols[1]:
                selected = st.selectbox("选择场馆", range(len(venues)), format_func=lambda i: labels[i])
            venue = venues[selected]
            target_date = st.date_input("预约日期", value=date.today() + timedelta(days=1), min_value=date.today())
            date_str = target_date.isoformat()
            query_key = (campus, venue["venue"], venue["activity"], venue["type"], date_str)
            if st.session_state.get("time_query_key") != query_key:
                st.session_state["time_query_key"] = query_key
                st.session_state.pop("times", None)
                st.session_state.pop("times_error", None)
                st.session_state.pop("time_map", None)
            if st.button("查询预约时段", type="primary"):
                op_log(f"查询时段：校区{campus}，场馆{venue['name']}，日期{date_str}")
                with st.spinner("正在查询可预约时段…"):
                    rows, error = parse_time_list(
                        apis.getTimeList(venue["campus"], date_str, venue["type"], venue["activity"])
                    )
                st.session_state["times"] = rows
                st.session_state["times_error"] = error
                if error:
                    op_log(error, "ERROR")
            times = st.session_state.get("times")
            times_error = st.session_state.get("times_error")
            if times_error:
                st.error(times_error)
            elif times is None:
                st.info("请选择校区、场馆和日期后，点击“查询预约时段”。")
            else:
                time_map, unavailable = slot_options(times)
                if unavailable:
                    st.caption("不可预约：" + "、".join(unavailable))
                if not time_map:
                    st.warning("该日期暂无可预约时段")
                else:
                    time_label = st.selectbox("预约时段", list(time_map))
                    period = time_map[time_label]
                    mode = st.radio("运行模式", ["执行一次", "持续轮询"], horizontal=True)
                    infinite_poll = False
                    if mode == "持续轮询":
                        infinite_poll = st.checkbox(
                            "无限轮询，直到预约成功",
                            value=False,
                            help="持续运行直到成功或接口返回终止性失败；点击页面顶部的停止预约可结束轮询",
                        )
                    delay = st.number_input("轮询间隔（毫秒）", min_value=100, max_value=60000, value=1000, step=100,
                                            disabled=(mode == "执行一次"))
                    rounds = st.number_input("最大轮询轮次", min_value=1, max_value=10000, value=60, step=1,
                                             disabled=(mode == "执行一次" or infinite_poll))
                    active_job = st.session_state.get("booking_job_id")
                    start_clicked = False
                    if not (active_job and JOBS.get(active_job, {}).get("status") == "running"):
                        start_clicked = st.button("开始预约", type="primary")
                    if start_clicked:
                        course = {"CGDM": venue["venue"], "XMDM": venue["activity"], "XQWID": venue["campus"],
                                  "KYYSJD": period, "YYRQ": date_str, "YYLX": venue["type"]}
                        op_log(f"开始预约：{venue['name']} {date_str} {period}")
                        job_id = uuid.uuid4().hex
                        job = {"status": "running", "attempt": 0, "detail": "任务已启动…", "success": False,
                               "logs": [], "stop_event": threading.Event()}
                        with JOBS_LOCK: JOBS[job_id] = job
                        st.session_state["booking_job_id"] = job_id
                        threading.Thread(target=booking_worker, args=(job_id, course, infinite_poll,
                                          int(rounds), int(delay)), daemon=True).start()
                        st.rerun()

    st.markdown('<div class="evidence-note"><strong>Privacy note</strong>Cookie 仅用于本次会话的接口请求，不会写入配置文件；姓名与学号仅保存在本机的便捷配置中。</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
