"""v0.63：「保存配置」在原配置文件基础上只更新本次改动（两侧同一机制）。

* 原文件其它键 / 自定义未知键 / 键顺序 / 缩进原样保留；
* 启动参数、负荷辨识「套用」等未经保存的运行期改动不随后续保存落盘；
* 服务启动后外部手改的内容不被内存配置覆盖；
* nilm 调参 persist=true 只写 nilm 的差异；非法值 400 且文件不动；
* 持久化文件不存在时：有加载模板→以模板为基准；都没有→写完整配置；
* 界面「保存总线侧配置」请求（source + 量纲 + 列映射）落盘且 source.path 相对仓库根。
"""
from __future__ import annotations

import json
import os
import pathlib
import shutil

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _flat(d, p=""):
    out = {}
    for k, v in d.items():
        if isinstance(v, dict):
            out.update(_flat(v, p + k + "."))
        else:
            out[p + k] = v
    return out


def _diff(a, b):
    fa, fb = _flat(a), _flat(b)
    return {k: (fa.get(k, "<无>"), fb.get(k, "<无>")) for k in set(fa) | set(fb) if fa.get(k, "<无>") != fb.get(k, "<无>")}


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    pytest.importorskip("httpx")
    from pytest import MonkeyPatch
    from starlette.testclient import TestClient
    from elec_tool.config import AppConfig
    d = tmp_path_factory.mktemp("r63")
    cfg_path = d / "runtime.json"
    base = AppConfig().to_dict()
    base["transform"]["pt_ratio"] = 123.0
    base["nilm"]["window_cycles"] = 444
    base["nilm"]["algorithms"]["glr"]["threshold"] = 77
    base["source"] = {"kind": "simulator", "path": "", "file_speed": 1.0}
    base["my_custom_note"] = "用户自加的键"
    cfg_path.write_text(json.dumps(base, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    mp = MonkeyPatch()
    mp.setenv("ELEC_TOOL_CONFIG_PATH", str(cfg_path))
    mp.setenv("ELEC_TOOL_BRANCH_CONFIG_PATH", str(d / "branch.json"))
    mp.setenv("ELEC_TOOL_AUTOSTART", "")
    mp.setenv("ELEC_TOOL_PERSIST_CONFIG", "1")
    mp.setenv("ELEC_TOOL_RUN_DIRS", "0")
    mp.setenv("ELEC_TOOL_OUTPUT_DIR", str(d / "out"))
    mp.setenv("ELEC_TOOL_EVENTS_DIR", str(d / "out" / "events"))
    mp.setenv("ELEC_TOOL_REALTIME_DIR", str(d / "out" / "rt"))
    mp.setenv("ELEC_TOOL_NILM_DIR", str(d / "out" / "nilm"))
    import app.server as srv
    with TestClient(srv.app) as c:
        yield {"c": c, "dir": d, "cfg": cfg_path, "srv": srv, "before": json.loads(cfg_path.read_text(encoding="utf-8"))}
    mp.undo()


def _read(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def test_save_only_patch_keeps_rest(env):
    c, cfg_path, before = env["c"], env["cfg"], env["before"]
    assert env["srv"].RUNNERS["bus"].persist_path == str(cfg_path)
    c.post("/api/engine/stop")
    # 1) 启动引擎（离线文件）—— 不写文件
    r = c.post("/api/engine/start", json={"kind": "csv_file", "path": "data/nilm_steps.csv", "file_speed": 0, "custom_time": False})
    assert r.status_code == 200, r.text
    assert _read(cfg_path) == before
    # 2) 负荷辨识「套用到运行配置」—— 不写文件
    r = c.post("/api/nilm/tune/apply", json={"params": {"min_delta_pct": 9.9}})
    assert r.status_code == 200, r.text
    assert _read(cfg_path) == before
    # 3) 外部手改 pt_ratio=321
    doc = _read(cfg_path); doc["transform"]["pt_ratio"] = 321.0
    cfg_path.write_text(json.dumps(doc, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    # 4) 界面只改一项并保存
    r = c.put("/api/config", json={"output": {"realtime_save": False}})
    assert r.status_code == 200 and r.json()["config_file_updated"] is True
    after = _read(cfg_path)
    assert _diff(before, after) == {"output.realtime_save": (True, False), "transform.pt_ratio": (123.0, 321.0)}
    assert after["my_custom_note"] == "用户自加的键"
    assert list(after) == list(before)                                   # 键顺序
    assert cfg_path.read_text(encoding="utf-8").startswith('{\n    "')     # 4 空格缩进保留
    # 内存配置仍是热更新后的（启动参数/套用值在内存里，不在文件里）
    cur = c.get("/api/config").json()
    assert cur["source"]["kind"] == "csv_file" and cur["nilm"]["min_delta_pct"] == 9.9
    assert after["source"]["kind"] == "simulator" and after["nilm"]["min_delta_pct"] == 0.0
    c.post("/api/engine/stop")


def test_tune_apply_persist_writes_only_nilm_diff(env):
    c, cfg_path = env["c"], env["cfg"]
    before = _read(cfg_path)
    r = c.post("/api/nilm/tune/apply", json={"params": {"min_delta_pct": 5.5}, "persist": True})
    assert r.status_code == 200 and r.json()["config_file_updated"] is True
    after = _read(cfg_path)
    assert _diff(before, after) == {"nilm.min_delta_pct": (0.0, 5.5)}
    assert after["nilm"]["window_cycles"] == 444 and after["nilm"]["algorithms"]["glr"]["threshold"] == 77


def test_invalid_value_400_file_untouched(env):
    c, cfg_path = env["c"], env["cfg"]
    raw = cfg_path.read_bytes()
    r = c.put("/api/config", json={"sampling": {"fs": 0}})
    assert r.status_code == 400
    assert cfg_path.read_bytes() == raw


def test_bus_source_save_request(env):
    """界面「保存总线侧配置」：source + transform/sampling/harmonic/power/columns 一次写入；路径存相对仓库根。"""
    c, cfg_path = env["c"], env["cfg"]
    before = _read(cfg_path)
    abs_path = str(ROOT / "data" / "nilm_steps.csv")
    body = {"source": {"kind": "csv_file", "path": abs_path, "file_speed": "2", "custom_time": False},
            "transform": {"enabled": True, "voltage_input": before["transform"]["voltage_input"], "pt_ratio": 100},
            "sampling": {"adaptive_freq": before["sampling"]["adaptive_freq"]}, "harmonic": {},
            "power": {"apparent": before["power"]["apparent"], "reactive": before["power"]["reactive"]},
            "columns": {"mapping_enabled": False}, "not_a_real_key": {"x": 1}}
    r = c.put("/api/config", json=body)
    assert r.status_code == 200, r.text
    after = _read(cfg_path)
    assert after["source"]["kind"] == "csv_file" and after["source"]["path"] == "data/nilm_steps.csv"
    assert after["source"]["file_speed"] == 2.0 and isinstance(after["source"]["file_speed"], float)
    assert after["transform"]["pt_ratio"] == 100 and after["my_custom_note"] == "用户自加的键"
    assert "not_a_real_key" not in after                                  # 未知键不写入
    assert after["nilm"]["window_cycles"] == 444
    d = _diff(before, after)
    assert set(d) <= {"source.kind", "source.path", "source.file_speed", "source.custom_time", "transform.pt_ratio",
                      "transform.enabled", "columns.mapping_enabled"}


def test_branch_without_file_writes_full_config(env):
    """分路侧持久化文件与模板都不存在 → 写完整配置（含本次改动），之后再保存只更新改动键。"""
    c, d = env["c"], env["dir"]
    bp = d / "branch.json"
    assert not bp.exists()
    r = c.put("/api/branch/config", json={"transform": {"ct_ratio": 15}})
    assert r.status_code == 200, r.text
    doc = _read(bp)
    assert doc["transform"]["ct_ratio"] == 15 and "sampling" in doc and "nilm" in doc
    doc["my_branch_note"] = 1
    bp.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    r = c.put("/api/branch/config", json={"transform": {"ct_ratio": 20}})
    assert r.status_code == 200
    doc2 = _read(bp)
    assert doc2["transform"]["ct_ratio"] == 20 and doc2["my_branch_note"] == 1


def test_missing_runtime_uses_default_template(env, tmp_path):
    """runtime 文件不存在、加载的是出厂 default.json → 以 default.json 内容为基准写 runtime（不动 default.json）。"""
    srv = env["srv"]
    from elec_tool.config import AppConfig
    tmpl = tmp_path / "default.json"; shutil.copy(ROOT / "configs" / "default.json", tmpl)
    tdoc = _read(tmpl); tdoc["tmpl_note"] = "出厂模板键"
    tmpl.write_text(json.dumps(tdoc, ensure_ascii=False, indent=2), encoding="utf-8")
    rt = tmp_path / "runtime.json"
    runner = srv.RUNNERS["bus"]
    old = (runner.cfg_path, runner.persist_path)
    try:
        runner.cfg_path, runner.persist_path = str(tmpl), str(rt)
        tok = srv._SIDE.set("bus")
        try:
            srv._persist(AppConfig.from_dict(runner.cfg.to_dict()), {"output": {"realtime_save": False}})
        finally:
            srv._SIDE.reset(tok)
        out = _read(rt)
        assert out["tmpl_note"] == "出厂模板键" and out["output"]["realtime_save"] is False
        assert _read(tmpl) == tdoc                                          # 模板本身不改
    finally:
        runner.cfg_path, runner.persist_path = old


def test_v75_only_changed_leaves_written_even_when_whole_config_sent(env):
    """v0.75：保存只写与原文件不同的叶子。① 送回与文件一致的分段 → 文件字节不变、config_file_changes 空；
    ② 外部手改文件 + 内存里有热套用值后，导出页「保存配置」整份送回 → 只有真正不同的键被写入，手改项不被覆盖；
    ③ 返回 config_file_changes 列出实际写入的键。"""
    c, cfg_path = env["c"], env["cfg"]
    c.post("/api/engine/stop")
    cur = c.get("/api/config").json()
    # 先把文件与内存在 output 段对齐，再送回与文件完全一致的 output 段
    raw0 = cfg_path.read_text(encoding="utf-8")
    doc = json.loads(raw0)
    r = c.put("/api/config", json={"output": doc["output"]})
    assert r.status_code == 200
    j = r.json()
    assert j["config_file_changes"] == [] and cfg_path.read_text(encoding="utf-8") == raw0      # 一字未改
    # 外部手改：transform.ct_ratio=9 + 自定义键；内存里 nilm.min_delta_pct 为之前热套用的 9.9（文件里 0.0）
    doc = json.loads(cfg_path.read_text(encoding="utf-8")); doc["transform"]["ct_ratio"] = 9.0; doc["my_custom_note"] = "改过"
    cfg_path.write_text(json.dumps(doc, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    r = c.post("/api/nilm/tune/apply", json={"params": {"min_delta_pct": 7.7}, "hot": True, "persist": False})   # 热套用、未保存
    assert r.status_code == 200
    whole = c.get("/api/config").json()
    r = c.put("/api/config", json=whole)                                        # 导出页「保存配置」：整份送回
    assert r.status_code == 200
    ch = r.json()["config_file_changes"]
    after = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert after["my_custom_note"] == "改过"                                    # 自定义键保留
    # 整份送回＝保存"当前运行配置"：与文件不同的键（含外部手改成 9 而内存仍是 15 的 ct_ratio、热套用的 nilm 值）按内存写回，
    # 其余一律不动
    assert "transform.ct_ratio" in ch and after["transform"]["ct_ratio"] == 15.0
    assert all(k.startswith(("nilm.", "transform.ct_ratio", "source.")) for k in ch), ch   # 只有真正不同的键
    assert "nilm.min_delta_pct" in ch and after["nilm"]["min_delta_pct"] == 7.7
    assert "output.realtime_save" not in ch and "sampling.fs" not in ch
    assert cfg_path.read_text(encoding="utf-8").startswith('{\n    "')


def test_v75_1_missing_keys_equal_to_builtin_default_not_added(env):
    """v0.75.1：文件里没有的键、取值又等于程序内置默认值 ⇒ 不补写（「不改任何值直接点保存」文件一字不动）；
    改成非默认值后该键才被补进文件，且只补这一项。"""
    c, cfg_path = env["c"], env["cfg"]
    c.post("/api/engine/stop")
    doc = json.loads(cfg_path.read_text(encoding="utf-8")); doc.pop("events", None)
    cfg_path.write_text(json.dumps(doc, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    raw0 = cfg_path.read_text(encoding="utf-8")
    ev = c.get("/api/config").json()["events"]
    ev["hysteresis"] = 0.95                                  # 内置默认值
    r = c.put("/api/config", json={"events": ev})
    assert r.status_code == 200
    ch = r.json()["config_file_changes"]
    assert "events.hysteresis" not in ch, ch                 # 等于内置默认值的缺失键不补写
    if ch:                                                  # 允许写入的只有运行期与默认不同的键（如 events_dir 由环境变量指定）
        assert all(k == "events.events_dir" for k in ch), ch
    else:
        assert cfg_path.read_text(encoding="utf-8") == raw0  # 一字不动
    ev["u1_high_pct"] = 123.0
    r = c.put("/api/config", json={"events": ev})
    assert r.status_code == 200
    assert "events.u1_high_pct" in r.json()["config_file_changes"]
    after = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert after["events"]["u1_high_pct"] == 123.0
