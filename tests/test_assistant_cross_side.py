"""智能问答指令的真实接口回归：两侧处于不同运行状态（2026-11-10 第三项任务，REPORT_TEST.md T-023）。

覆盖补-A1～A7、补-A9～A11。每条用例都通过真实的 HTTP 接口（同进程 TestClient）提问和确认，两侧的
数据源由真实的引擎线程运行；凡是跨侧的用例，总线侧与分路侧的运行状态都不相同，这样“读错了一侧的
状态”一定会表现为断言失败。模型用 Fake 响应，不访问网络。

这些用例只依赖 HTTP 接口，修复前后的接口形状相同，所以可以原样拿去跑修复前的代码做负对照。
"""
from __future__ import annotations

import csv
import json
import logging
import pathlib
import shutil
import time

import numpy as np
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FS = 6400
ADMIN = "cross-side-admin-token"
OPERATOR = "cross-side-operator-token"
LIMITED = "cross-side-limited-operator-token"   # 没有 events.read（补-A6）
MODEL_TEXT = "这是模型的普通回答。"
WARNING = "系统不支持只作用于总线侧"


def _write_csv(path, dur=8.0):
    n = int(dur * FS); t = np.arange(n) / FS; w = 2 * np.pi * 50 * t
    with open(path, "w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh); wr.writerow(["时间戳", "A相电压", "A相电流", "B相电压", "B相电流", "C相电压", "C相电流"])
        for k in range(n):
            row = [f"{1_700_000_000 + t[k]:.6f}"]
            for ph in (0, -2.0944, 2.0944):
                row += [f"{81.65 * np.sin(w[k] + ph):.4f}", f"{7.07 * np.sin(w[k] + ph - 0.3):.5f}"]
            wr.writerow(row)
    return str(path)


class _Live:
    """The running app, its assistant service, and helpers that talk to it over HTTP only."""

    def __init__(self, client, service, workdir):
        self.client, self.service, self.dir = client, service, workdir
        self.model_call = None            # None：模型只回文字；(工具名, 参数)：模型发起一次工具调用
        self.bus_csv = _write_csv(workdir / "bus.csv")
        self.branch_csv = _write_csv(workdir / "branch.csv")

    # ---- 数据源：直接走业务接口，把两侧摆成需要的状态 ----
    def state(self):
        """``{"bus": (running, paused), "branch": (running, paused)}`` as the state endpoints report it."""
        out = {}
        for side, url in (("bus", "/api/state"), ("branch", "/api/branch/state")):
            data = self.client.get(url).json()
            out[side] = (bool(data["running"]), bool(data["paused"]))
        return out

    def wait_state(self, expected, timeout=8.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.state() == expected:
                return
            time.sleep(0.02)
        assert self.state() == expected

    def stop_all(self):
        self.client.post("/api/branch/engine/stop")
        self.client.post("/api/engine/stop")
        self.wait_state({"bus": (False, False), "branch": (False, False)})

    def play(self, side):
        """Start slow playback of an 8 s recording on one side only (lasts about 32 s unless stopped)."""
        if side == "bus":
            response = self.client.post("/api/engine/start", json={
                "kind": "csv_file", "path": self.bus_csv, "block_samples": 640, "file_speed": 0.25,
                "with_branch": False})
        else:
            response = self.client.post("/api/branch/engine/start", json={
                "kind": "csv_file", "path": self.branch_csv, "block_samples": 640, "file_speed": 0.25,
                "file_speed_follow": False})
        assert response.status_code == 200, response.text

    def use_simulator(self, side):
        """Point one side's saved configuration back at the simulator (the factory default)."""
        url = "/api/branch/config" if side == "branch" else "/api/config"
        config = self.client.get(url).json()
        config["source"]["kind"] = "simulator"
        assert self.client.put(url, json=config).status_code == 200

    # ---- 助手：只走 HTTP 接口 ----
    def chat(self, prompt, page="bus", model_call=None, token=OPERATOR):
        """Ask from the bus-side or the branch-side page. Returns ``(status, answer_or_error, proposal)``."""
        self.model_call = model_call
        self.service._requests.clear()          # 每个客户端 60 秒 12 次的限流不是这里要测的内容
        url = "/api/branch/assistant/chat" if page == "branch" else "/api/assistant/chat"
        response = self.client.post(url, headers={"X-Assistant-Operator-Token": token}, json={
            "prompt": prompt, "model_type": "local", "model_name": "qwen3:8b", "stream": False})
        data = response.json()
        return response.status_code, str(data.get("error") or data.get("answer") or ""), data.get("proposal")

    def proposal(self, prompt, page="bus", model_call=None):
        status, text, proposal = self.chat(prompt, page, model_call)
        assert status == 200 and proposal, (prompt, status, text)
        return proposal

    def refusal(self, prompt, page="bus"):
        status, text, proposal = self.chat(prompt, page)
        assert proposal is None, (prompt, proposal)
        return status, text

    def confirm(self, proposal, page="bus"):
        self.service._tool_requests.clear()     # 每位操作员 60 秒确认 5 次的限流同上
        url = "/api/branch/assistant/tools/confirm" if page == "branch" else "/api/assistant/tools/confirm"
        response = self.client.post(url, headers={"X-Assistant-Operator-Token": OPERATOR}, json={
            "proposal_id": proposal["id"], "confirmation_code": proposal.get("confirmation_code") or ""})
        assert response.status_code == 200, response.text
        return response.json()["result"]

    def audit(self):
        response = self.client.get("/api/assistant/tools/audit?limit=200",
                                   headers={"X-Assistant-Admin-Token": ADMIN})
        assert response.status_code == 200, response.text
        return response.json()["records"]

    def pending_tools(self):
        return sorted((item["name"], item["side"]) for item in self.service._pending_tools.values())


@pytest.fixture(scope="module")
def live(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient

    from app.assistant import AssistantService
    from app.assistant_tools import TOOL_CATALOG, TOOL_NAMES

    d = tmp_path_factory.mktemp("cross_side")
    shutil.copy(ROOT / "configs" / "default.json", d / "cfg.json")
    shutil.copy(ROOT / "configs" / "branch.json", d / "branch.json")
    mp = MonkeyPatch()
    all_scopes = sorted({tool["scope"] for tool in TOOL_CATALOG})
    for key, value in {
        "ELEC_TOOL_CONFIG_PATH": str(d / "cfg.json"), "ELEC_TOOL_BRANCH_CONFIG_PATH": str(d / "branch.json"),
        "ELEC_TOOL_AUTOSTART": "", "ELEC_TOOL_PERSIST_CONFIG": "0", "ELEC_TOOL_RUN_DIRS": "0",
        "ELEC_TOOL_EVENTS_DIR": str(d / "ev"), "ELEC_TOOL_REALTIME_DIR": str(d / "rt"),
        "ELEC_TOOL_NILM_DIR": str(d / "nilm"), "ELEC_TOOL_OUTPUT_DIR": str(d / "output"),
        "ELEC_TOOL_LAST_RESULT_FILE": str(d / "last.json"),
        "ELEC_TOOL_ASSISTANT_ADMIN_TOKEN": ADMIN,
        "ELEC_TOOL_ASSISTANT_OPERATOR_TOKENS": json.dumps([
            {"id": "cross-side-operator", "token": OPERATOR, "scopes": all_scopes},
            {"id": "limited-operator", "token": LIMITED,
             "scopes": [scope for scope in all_scopes if scope != "events.read"]},
        ]),
    }.items():
        mp.setenv(key, value)

    import app.server as srv
    service = AssistantService(data_dir=str(d / "assistant"))
    service.update_config({"tools_enabled": True, "enabled_tools": list(TOOL_NAMES)}, ADMIN)
    mp.setattr(srv, "assistant_service", service)
    with TestClient(srv.app) as client:
        env = _Live(client, service, d)

        class Completion:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, _limit):
                if env.model_call is None:
                    message = {"content": MODEL_TEXT}
                else:
                    name, arguments = env.model_call
                    message = {"content": "", "tool_calls": [{"index": 0, "id": "call-0", "type": "function",
                               "function": {"name": name, "arguments": json.dumps(arguments)}}]}
                return json.dumps({"choices": [{"message": message}]}).encode("utf-8")

        mp.setattr(service, "_open_request", lambda _plan, stream: Completion())
        try:
            yield env
        finally:
            client.post("/api/branch/engine/stop")
            client.post("/api/engine/stop")
    mp.undo()


@pytest.fixture()
def scene(live):
    """Both sides stopped, simulator sources, no pending proposals; stopped again afterwards."""
    live.stop_all()
    live.use_simulator("bus"); live.use_simulator("branch")
    live.service._pending_tools.clear()
    yield live
    live.stop_all()


def _direct_read(answer):
    """The JSON summary that follows the first line of a direct read answer."""
    head, _, body = answer.partition("\n")
    return head, json.loads(body)


# --------------------------------------------------------------------------- 补-A9 / 补-A10

def test_cross_side_pause_resume_stop_are_refused_when_the_target_is_not_running(scene):
    """补-A9：总线侧在播放、分路侧未运行，在总线侧页面对分路侧说暂停 / 恢复 / 停止。

    登记时这三句话照样生成提案：暂停 / 恢复到确认才报 400，停止返回成功。
    """
    scene.play("bus")
    playing = {"bus": (True, False), "branch": (False, False)}
    scene.wait_state(playing)
    for prompt, message in (("暂停分路侧离线播放", "分路侧数据源未在运行，无法暂停"),
                            ("恢复分路侧离线播放", "分路侧数据源未在运行，无法恢复"),
                            ("停止分路侧数据源", "分路侧数据源未在运行，无法停止"),
                            ("仅停止分路侧数据源", "分路侧数据源未在运行，无法停止")):   # 最后一句走意图识别直达
        status, text = scene.refusal(prompt)
        assert status == 409 and message in text, (prompt, status, text)
    assert scene.pending_tools() == [] and scene.state() == playing
    # 同一时刻，总线侧自己的暂停不受影响
    proposal = scene.proposal("暂停当前侧离线播放")
    assert (proposal["tool"], proposal["side"]) == ("pause_current_source", "bus")


def test_cross_side_start_is_not_blocked_by_the_state_of_the_page_side(scene):
    """补-A10：总线侧在播放、分路侧未运行，在总线侧页面说“启动分路侧数据源”。

    登记时被 409“分路侧数据源已在运行或暂停”误拒——读的是总线侧的状态。
    """
    scene.play("bus")
    playing = {"bus": (True, False), "branch": (False, False)}
    scene.wait_state(playing)
    proposal = scene.proposal("启动分路侧数据源")
    assert (proposal["tool"], proposal["side"]) == ("start_current_source", "branch")
    assert scene.state() == playing                       # 生成提案不改变任何一侧
    scene.confirm(proposal)                               # 从总线侧的接口确认，执行在分路侧
    scene.wait_state({"bus": (True, False), "branch": (True, False)})

    # 现在分路侧在运行：同一句话被拒绝；停止可以执行，而且只停分路侧
    status, text = scene.refusal("启动分路侧数据源")
    assert status == 409 and "分路侧数据源已在运行或暂停，不会重复启动" in text
    proposal = scene.proposal("停止分路侧数据源")
    assert (proposal["tool"], proposal["side"]) == ("stop_current_source", "branch")
    scene.confirm(proposal)
    scene.wait_state(playing)


def test_bus_playing_branch_stopped_from_the_branch_page(scene):
    """同样的状态，在分路侧页面操作总线侧：检查读的是总线侧的状态。"""
    scene.play("bus")
    scene.wait_state({"bus": (True, False), "branch": (False, False)})

    # 补-A10 的另一半：目标侧已在运行，登记时提案照样生成、到确认才被 409 拒绝
    status, text = scene.refusal("启动总线侧数据源", page="branch")
    assert status == 409 and "总线侧数据源已在运行或暂停，不会重复启动" in text
    assert scene.pending_tools() == []
    # 分路侧自己未运行：对“当前侧”的暂停被拒绝，启动可以生成提案
    status, text = scene.refusal("暂停当前侧离线播放", page="branch")
    assert status == 409 and "分路侧数据源未在运行，无法暂停" in text
    assert scene.proposal("启动当前侧数据源检测", page="branch")["side"] == "branch"

    # 暂停总线侧：提案绑定总线侧；从分路侧的接口确认，暂停的是总线侧
    proposal = scene.proposal("暂停总线侧离线播放", page="branch")
    assert (proposal["tool"], proposal["side"]) == ("pause_current_source", "bus")
    scene.confirm(proposal, page="branch")
    scene.wait_state({"bus": (True, True), "branch": (False, False)})


def test_branch_playing_bus_stopped_from_the_bus_page(scene):
    """反过来：分路侧单独在播放、总线侧未运行，在总线侧页面完成分路侧的暂停、恢复、停止。"""
    scene.play("branch")
    scene.wait_state({"bus": (False, False), "branch": (True, False)})

    # 登记时这句话照样生成提案（读的是总线侧“未运行”）
    status, text = scene.refusal("启动分路侧数据源")
    assert status == 409 and "分路侧数据源已在运行或暂停，不会重复启动" in text
    # 总线侧自己未运行：不受分路侧在运行的影响
    status, text = scene.refusal("停止当前侧数据源")
    assert status == 409 and "总线侧数据源未在运行，无法停止" in text
    assert scene.proposal("启动当前侧数据源检测")["side"] == "bus"
    scene.service._pending_tools.clear()

    for prompt, tool, after in (
            ("暂停分路侧离线播放", "pause_current_source", (True, True)),
            ("恢复分路侧离线播放", "resume_current_source", (True, False)),
            ("停止分路侧数据源", "stop_current_source", (False, False))):
        proposal = scene.proposal(prompt)
        assert (proposal["tool"], proposal["side"]) == (tool, "branch"), prompt
        scene.confirm(proposal)
        scene.wait_state({"bus": (False, False), "branch": after})
        if after == (True, True):
            # 分路侧已暂停：此时“恢复”才放行，“启动”要求改用恢复
            status, text = scene.refusal("启动分路侧数据源")
            assert status == 409 and "请使用恢复操作" in text


# --------------------------------------------------------------------------- 补-A11

def test_resume_is_offered_only_while_the_source_is_paused(scene):
    """补-A11：恢复的前置检查看“是否已暂停”。登记时方向相反——已暂停时被拒绝，已停止时反而生成提案。"""
    # 两侧都未运行
    for prompt in ("恢复当前侧离线播放", "resume"):
        status, text = scene.refusal(prompt)
        assert status == 409 and "总线侧数据源未在运行，无法恢复" in text, prompt
    assert scene.pending_tools() == []

    # 总线侧在播放、未暂停
    scene.play("bus")
    scene.wait_state({"bus": (True, False), "branch": (False, False)})
    status, text = scene.refusal("恢复当前侧离线播放")
    assert status == 409 and "总线侧数据源正在运行，无需恢复" in text

    # 总线侧已暂停（running 仍为 True）：本侧页面和对侧页面都能生成恢复提案
    assert scene.client.post("/api/engine/pause").status_code == 200
    scene.wait_state({"bus": (True, True), "branch": (False, False)})
    assert scene.proposal("恢复总线侧离线播放", page="branch")["side"] == "bus"
    assert scene.proposal("resume")["tool"] == "resume_current_source"
    proposal = scene.proposal("恢复当前侧离线播放")
    assert (proposal["tool"], proposal["side"]) == ("resume_current_source", "bus")
    scene.confirm(proposal)
    scene.wait_state({"bus": (True, False), "branch": (False, False)})


# --------------------------------------------------------------------------- 补-A1 / 补-A4

def test_background_and_last_n_requests_are_not_refused_as_delayed(scene):
    """补-A1：登记时这三句话被 HTTP 400“系统不支持延时执行”拒绝。"""
    for prompt, tool in (("查看后台重采样任务状态", "get_resample_status"),
                         ("取消后台重采样", "cancel_resample"),
                         ("查询最后10条电能质量事件", "get_event_list")):
        proposal = scene.proposal(prompt)
        assert proposal["tool"] == tool, prompt
    for prompt in ("15秒过后启动当前侧数据源检测", "5分钟后列出当前电能质量事件"):
        status, text = scene.refusal(prompt)
        assert status == 400 and "系统不支持延时执行" in text, prompt


def test_simulator_source_can_be_started_through_either_direct_route(scene):
    """补-A4：数据源是模拟器时，登记时“启动分路侧数据源检测”返回 409，而“启动分路侧数据源”生成提案。"""
    for prompt in ("启动分路侧数据源检测", "启动分路侧数据源"):
        proposal = scene.proposal(prompt)
        assert (proposal["tool"], proposal["side"]) == ("start_current_source", "branch"), prompt
    # 话里说了离线 / CSV，而数据源不是文件：两条路由都拒绝
    for prompt in ("启动分路侧离线数据源检测", "播放分路侧离线数据源"):
        status, text = scene.refusal(prompt)
        assert status == 409 and "分路侧配置不是离线文件数据源" in text, prompt


# --------------------------------------------------------------------------- 补-A2

def test_modbus_is_not_read_as_the_bus_side(scene):
    """补-A2：登记时在分路侧页面问“查看 Modbus 运行状态”，返回的是总线侧的状态。"""
    scene.play("bus")
    scene.wait_state({"bus": (True, False), "branch": (False, False)})
    status, answer, proposal = scene.chat("查看 Modbus 运行状态", page="branch")
    head, summary = _direct_read(answer)
    assert status == 200 and proposal is None and "查询分路侧运行状态" in head
    assert summary["side"] == "branch" and summary["running"] is False

    # 点名另一侧、以及不点名：读到的运行状态各不相同
    _head, summary = _direct_read(scene.chat("查询当前运行状态")[1])
    assert summary["side"] == "bus" and summary["running"] is True and summary["source_kind"] == "csv_file"
    _head, summary = _direct_read(scene.chat("查看分路侧运行状态")[1])
    assert summary["side"] == "branch" and summary["running"] is False
    head, summary = _direct_read(scene.chat("查看总线侧计算配置", page="branch")[1])
    assert "查询总线侧计算配置摘要" in head and summary["side"] == "bus" and "sampling" in summary


def test_a_prompt_naming_both_sides_is_never_resolved_to_the_first_one(scene):
    """补-A2：两侧都点名时不替用户选。登记时取先出现的一侧——这里会得到一张停止总线侧的提案。"""
    scene.play("bus")
    scene.wait_state({"bus": (True, False), "branch": (False, False)})
    for prompt in ("停止总线侧 分路侧数据源", "停止分路侧总线侧数据源"):
        status, text = scene.refusal(prompt)
        assert status == 400 and "同时提到了总线侧和分路侧" in text, prompt
    assert scene.pending_tools() == []
    # 意图识别直达同样不介入，交给模型；模型只回文字时就是普通回答
    assert scene.chat("仅停止总线侧和分路侧数据源") == (200, MODEL_TEXT, None)
    assert scene.pending_tools() == [] and scene.state() == {"bus": (True, False), "branch": (False, False)}


# --------------------------------------------------------------------------- 补-A7

def test_direct_reads_leave_an_audit_record(scene):
    """补-A7：登记时两个只读查询直接执行，不写 tool_audit.jsonl。"""
    before = len(scene.audit())
    assert "查询总线侧运行状态" in scene.chat("查询当前运行状态")[1]
    assert "查询分路侧计算配置摘要" in scene.chat("查看分路侧计算配置")[1]
    records = scene.audit()[before:]
    assert [(row["tool"], row["side"], row["status"]) for row in records] == [
        ("get_runtime_status", "bus", "direct_read"), ("get_runtime_settings", "branch", "direct_read")]
    assert all(row["operator_id"] == "cross-side-operator" and row["origin"] == "intent" and row["arguments"] == {}
               and "proposal_id" not in row and len(row["trace_id"]) == 16 for row in records)
    assert scene.pending_tools() == []


def test_low_tier_read_request_is_left_to_the_model(scene, caplog):
    """补-A7：low 档位（两个候选同分）登记时照样直接执行其中一个；现在交给模型路径。"""
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    before = len(scene.audit())
    for prompt in ("查看当前运行状态和计算配置", "查看总线侧和分路侧的运行状态"):
        caplog.clear()
        assert scene.chat(prompt) == (200, MODEL_TEXT, None), prompt
        assert "decision=model_fallback" in caplog.text and "intent_tier=low" in caplog.text, prompt
    assert len(scene.audit()) == before and scene.pending_tools() == []


# --------------------------------------------------------------------------- 补-A3

def test_exclusive_wording_warns_that_the_bus_side_cannot_act_alone(scene):
    """补-A3：“只 / 仅 / 单独”不改变执行内容；总线侧的联动操作在卡片上写明不能只作用于总线侧。"""
    proposal = scene.proposal("只启动总线侧数据源", page="branch")
    assert proposal["side"] == "bus" and WARNING in proposal["impact"] and "一起启动" in proposal["impact"]
    assert WARNING not in scene.proposal("启动总线侧数据源", page="branch")["impact"]
    assert WARNING not in scene.proposal("只启动分路侧数据源")["impact"]      # 分路侧的操作不联动总线侧

    scene.play("bus")
    scene.wait_state({"bus": (True, False), "branch": (False, False)})
    for prompt, effect in (("只暂停当前侧离线播放", "一起暂停"), ("仅停止总线侧数据源", "一起停止")):
        proposal = scene.proposal(prompt)
        assert proposal["side"] == "bus" and WARNING in proposal["impact"] and effect in proposal["impact"], prompt
    assert WARNING not in scene.proposal("暂停当前侧离线播放")["impact"]


# --------------------------------------------------------------------------- 补-A5

def test_model_path_proposal_runs_on_the_side_named_in_the_prompt(scene):
    """补-A5：登记时在总线侧页面说“把分路侧接线模式……”得到 side=bus 的提案，确认后改的是总线侧。"""
    wiring = lambda: (scene.client.get("/api/config").json()["transform"]["wiring"],            # noqa: E731
                      scene.client.get("/api/branch/config").json()["transform"]["wiring"])
    assert wiring() == ("3p4w", "3p4w")
    call = ("set_wiring_mode", {"wiring": "3p3w"})

    proposal = scene.proposal("把分路侧接线模式切换到3p3w", model_call=call)
    assert proposal["side"] == "branch" and proposal["summary"] == "将分路侧接线模式切换为 3p3w"
    assert proposal["title"] == "切换分路侧接线模式"       # 跨侧提案的标题不写“当前侧”
    result = scene.confirm(proposal)
    assert result["side"] == "branch" and wiring() == ("3p4w", "3p3w")

    # 不点名侧别：仍是提问页面所在的一侧
    proposal = scene.proposal("把接线模式切换到3p3w", model_call=call)
    assert proposal["side"] == "bus" and proposal["title"] == "切换当前侧接线模式"
    # 两侧都点名：澄清，不创建提案
    status, answer, proposal = scene.chat("把总线侧和分路侧接线模式切换到3p3w", model_call=call)
    assert status == 200 and proposal is None and "同时提到了总线侧和分路侧" in answer
    assert wiring() == ("3p4w", "3p3w")

    # 复原分路侧（从分路侧页面点名总线侧的反方向也一并核对）
    proposal = scene.proposal("把分路侧接线模式切换到3p4w", page="branch",
                              model_call=("set_wiring_mode", {"wiring": "3p4w"}))
    scene.confirm(proposal, page="branch")
    proposal = scene.proposal("把总线侧接线模式切换到3p3w", page="branch", model_call=call)
    assert proposal["side"] == "bus" and proposal["title"] == "切换总线侧接线模式"
    assert wiring() == ("3p4w", "3p4w")


def test_cross_side_export_is_downloaded_from_the_side_that_produced_it(scene):
    """补-A5 的连带后果：分路侧的导出文件要从分路侧的地址下载（前端按结果里的 side 拼地址）。"""
    scene.play("branch")
    scene.wait_state({"bus": (False, False), "branch": (True, False)})
    deadline = time.time() + 10.0
    while time.time() < deadline and not scene.client.get("/api/branch/state").json().get("stored_results"):
        time.sleep(0.05)

    proposal = scene.proposal("导出分路侧电气量结果CSV", model_call=("export_csv", {"dataset": "electrical_results"}))
    assert (proposal["tool"], proposal["side"]) == ("export_csv", "branch")
    result = scene.confirm(proposal)
    assert result["side"] == "branch" and result["bytes"] > 0
    headers = {"X-Assistant-Operator-Token": OPERATOR}
    url = result["download_url"]
    assert url.startswith("/api/assistant/tools/export/")
    branch_url = "/api/branch/" + url[len("/api/"):]
    downloaded = scene.client.get(branch_url, headers=headers)
    assert downloaded.status_code == 200 and len(downloaded.content) == result["bytes"]
    # 总线侧没有运行过，没有结果可导；这个文件确实来自分路侧，从总线侧的地址取不到
    wrong_side = scene.client.get(url, headers=headers)
    assert wrong_side.status_code == 403 and "另一侧" in wrong_side.json()["error"]


# --------------------------------------------------------------------------- 补-A6

def test_unavailable_intent_tool_falls_through_to_the_model_and_is_logged(scene, caplog):
    """补-A6：识别出的工具本轮不可用时不报 403，转入模型路径；路由日志写明识别出的工具和它不可用。"""
    caplog.set_level(logging.INFO, logger="elec_tool.assistant")
    for prompt in ("列出当前电能质量事件", "电能质量事件有哪些类型"):
        caplog.clear()
        status, answer, proposal = scene.chat(prompt, token=LIMITED)
        assert (status, answer, proposal) == (200, MODEL_TEXT, None), prompt
        route = [record.getMessage() for record in caplog.records
                 if record.getMessage().startswith("assistant_route_decision")]
        assert len(route) == 1 and "decision=model_fallback" in route[0] and "intent_tier=high" in route[0]
        assert "intent_tool=get_event_list intent_tool_available=False" in route[0]
    # 有权限的操作员说同一句话：直达，生成提案
    caplog.clear()
    assert scene.proposal("列出当前电能质量事件")["tool"] == "get_event_list"
    assert "intent_tool=get_event_list intent_tool_available=True" in caplog.text
