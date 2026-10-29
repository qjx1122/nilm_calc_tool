"""v0.99.20：画像匹配候选诊断落盘 + 运行目录复制画像文件。"""
import csv, os
import numpy as np

from elec_tool.config import AppConfig
from elec_tool.nilm import NilmWriter


def test_candidate_csv_written(tmp_path):
    cfg = AppConfig(); cfg.nilm.save = True
    w = NilmWriter(cfg.nilm, root=str(tmp_path), source_id=0, run_id=7, dir_override=str(tmp_path / "nilm"))
    w.write_profile_candidate({"t_start": 1.5, "t_start_local": "x", "g_on": 10, "direction": "STOP", "status": "rejected", "flags": ["d2_exceeds"],
                               "scale": 2, "scales_hit": [2, 4], "confidence": 0.0, "d2": 300.0, "d2_per_dim": 42.8, "margin": 1.2,
                               "vec": {"d_ia": -1.0, "d_p": 5.0}, "contrib": {"d_ia": 9.0}})
    files = [f for f in os.listdir(tmp_path / "nilm") if f.startswith("nilm_profile_candidates_")]
    assert len(files) == 1
    rows = list(csv.DictReader(open(tmp_path / "nilm" / files[0], encoding="utf-8-sig")))
    assert rows[0]["status"] == "rejected" and rows[0]["flags"] == "d2_exceeds" and rows[0]["scales_hit"] == "2/4" and rows[0]["d_ia"] == "-1.0"
    cfg.nilm.save = False
    w2 = NilmWriter(cfg.nilm, root=str(tmp_path), dir_override=str(tmp_path / "n2")); w2.write_profile_candidate({"g_on": 1})
    assert not os.path.exists(tmp_path / "n2")
