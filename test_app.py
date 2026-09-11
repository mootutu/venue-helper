import threading
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from streamlit.testing.v1 import AppTest

import app


def test_stop_control_survives_rerun_without_times():
    job_id = uuid.uuid4().hex
    setup = f'''
if "booking_job_id" not in st.session_state:
    st.session_state["connected"] = True
    st.session_state["booking_job_id"] = {job_id!r}
    JOBS[{job_id!r}] = {{"status": "running", "attempt": 1,
        "detail": "waiting", "logs": [], "stop_event": threading.Event()}}
main()
st.session_state["stop_received"] = JOBS[{job_id!r}]["stop_event"].is_set()
'''
    source = Path("app.py").read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
    page = AppTest.from_string(source + setup).run()
    page.run()
    assert not page.exception
    assert next(button for button in page.button if button.label == "退出当前会话").disabled
    page.button(key=f"stop-{job_id}").click().run()
    assert not page.exception
    assert page.session_state["stop_received"]


def test_failure_message_does_not_count_as_success():
    assert not app.is_success({"code": "error", "msg": "预约未成功"})
    assert app.is_success({"code": "0"})
    assert app.is_terminal({"msg": "本次操作的预约人学工号不是当前登录人"})


def test_login_gates_booking_workspace():
    source = Path("app.py").read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
    page = AppTest.from_string(source + "main()\n").run()
    assert not page.exception
    assert len(page.selectbox) == 0
    assert "登录并进入预约" in [button.label for button in page.button]
    assert any("登录场馆预约" in item.value for item in page.markdown)


def test_connected_session_shows_booking_workspace():
    source = Path("app.py").read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
    setup = '''
st.session_state["connected"] = True
st.session_state["venues"] = [{"name": "测试场馆", "activity": "A", "activity_name": "羽毛球", "venue": "V", "campus": "1", "type": "1.0", "kind": "包场"}]
main()
'''
    page = AppTest.from_string(source + setup).run()
    assert not page.exception
    assert len(page.selectbox) >= 1
    assert "登录并进入预约" not in [button.label for button in page.button]
    assert any("选择你的运动时段" in item.value for item in page.markdown)


@pytest.mark.parametrize("config", [None, {"code": 401, "msg": "登录已失效"}, {"packageVenueList": []}])
def test_login_submission_and_logout(monkeypatch, tmp_path, config):
    get_config = Mock(return_value=config)
    monkeypatch.setattr(app.apis, "getSysConfig", get_config)
    monkeypatch.setattr(app.apis, "cookies", {})
    monkeypatch.setattr(app.apis, "stuid", "")
    monkeypatch.setattr(app.apis, "stuname", "")
    monkeypatch.setattr(app.apis, "_session", SimpleNamespace(cookies={}))
    source = Path("app.py").read_text(encoding="utf-8").split('if __name__ == "__main__":')[0]
    setup = f'''
PROFILE_PATH = Path({str(tmp_path / 'profile.json')!r})
LOG_PATH = Path({str(tmp_path / 'operations.log')!r})
main()
'''
    page = AppTest.from_string(source + setup).run()
    get_config.assert_not_called()
    page.text_input(key="stuid_input").set_value("test-student")
    page.text_input(key="stuname_input").set_value("测试用户")
    page.text_input(key="cookie_input").set_value("test-session=test-cookie")
    next(button for button in page.button if button.label == "登录并进入预约").click().run()
    assert not page.exception
    get_config.assert_called_once()

    if config is None or "code" in config:
        assert len(page.error) == 1
        assert len(page.selectbox) == 0
        assert "登录并进入预约" in [button.label for button in page.button]
        assert not (tmp_path / "profile.json").exists()
        assert not app.apis.cookies
    else:
        assert page.session_state["connected"]
        assert len(page.text_input) == 0
        assert any("当前暂无可预约场馆" in item.value for item in page.info)
        page.run()
        assert page.session_state["connected"]
        next(button for button in page.button if button.label == "退出当前会话").click().run()
        assert not page.exception
        assert not page.session_state["connected"]
        assert len(page.selectbox) == 0
        assert page.text_input(key="cookie_input").value == ""
        assert not app.apis.cookies
