"""Bundled project documentation for the in-app tuning assistant.

Only explicitly allow-listed, tracked documentation and shipped configuration
templates are read. Runtime configuration, user data, and ``tmp/`` are never
used to construct the built-in corpus.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

log = logging.getLogger("elec_tool.assistant.docs")

PLATFORM_PARAMETER_DOC_ID = "builtin-platform-parameters"
MAX_BUNDLED_SOURCE_BYTES = 2_000_000


def _read_text(root: Path, relative_path: str) -> str:
    path = root / relative_path
    try:
        raw = path.read_bytes()
    except OSError as exc:
        log.warning("Bundled assistant document is unavailable (%s): %s", relative_path, exc)
        return ""
    if len(raw) > MAX_BUNDLED_SOURCE_BYTES:
        log.warning("Bundled assistant document is over the size limit: %s", relative_path)
        return ""
    try:
        return raw.decode("utf-8-sig").strip()
    except UnicodeDecodeError:
        log.warning("Bundled assistant document is not UTF-8: %s", relative_path)
        return ""


def _extract_markdown_sections(markdown: str, selectors: Sequence[str]) -> str:
    """Extract complete Markdown sections selected by heading-line regexes."""
    lines = str(markdown or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    headings: List[tuple[int, int, str]] = []
    fence_char = ""
    for index, line in enumerate(lines):
        stripped = line.strip()
        fence = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence:
            marker = fence.group(1)[0]
            if not fence_char:
                fence_char = marker
            elif marker == fence_char:
                fence_char = ""
            continue
        if fence_char:
            continue
        match = re.match(r"^(#{1,6})\s+.+$", stripped)
        if match:
            headings.append((index, len(match.group(1)), line))
    patterns = [re.compile(selector) for selector in selectors]
    selected: List[str] = []
    for heading_index, (start, level, line) in enumerate(headings):
        if not any(pattern.match(line.strip()) for pattern in patterns):
            continue
        end = len(lines)
        for next_start, next_level, _ in headings[heading_index + 1:]:
            if next_level <= level:
                end = next_start
                break
        section = "\n".join(lines[start:end]).strip()
        if section:
            selected.append(section)
    return "\n\n---\n\n".join(selected)


def _document(doc_id: str, title: str, category: str, summary: str, content: str) -> Dict[str, Any]:
    body = str(content or "").strip()
    if not body:
        body = "本地正式文档暂不可用。请检查软件安装包是否包含本项目文档后重启服务。"
    return {
        "id": doc_id,
        # ``name`` is the safe, stable citation label; source filesystem paths are not exposed.
        "name": title,
        "title": title,
        "category": category,
        "summary": summary,
        "content": body,
        "characters": len(body),
    }


def _flatten_config(value: Any, prefix: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict) and value:
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _flatten_config(child, path)
        return
    yield prefix or "(root)", value


def _json_cell(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text.replace("|", "\\|").replace("\n", " ")


def _build_parameter_catalog(root: Path) -> str:
    default_text = _read_text(root, "configs/default.json")
    branch_text = _read_text(root, "configs/branch.json")
    try:
        bus = json.loads(default_text) if default_text else {}
        branch = json.loads(branch_text) if branch_text else {}
    except (ValueError, TypeError):
        log.warning("Shipped assistant parameter templates are invalid JSON")
        bus, branch = {}, {}
    try:
        # AppConfig defaults fill parameters not explicitly serialized in older templates
        # (e.g. event/NILM/processing blocks); show that provenance as a separate column.
        from elec_tool.config import AppConfig
        code_defaults = AppConfig().to_dict()
    except Exception:
        log.warning("Could not build assistant parameter catalog from AppConfig defaults")
        code_defaults = {}

    code_values = dict(_flatten_config(code_defaults))
    bus_values = dict(_flatten_config(bus))
    branch_values = dict(_flatten_config(branch))
    paths = list(dict.fromkeys([*code_values, *bus_values, *branch_values]))
    rows = [
        "# 平台参数清单（代码默认 / 总线侧 / 分路侧）",
        "",
        "> 本清单在助手服务初始化时由 `AppConfig` 代码默认值、仓库跟踪的 `configs/default.json` 与 `configs/branch.json` 自动生成。三列来源分开展示，不代表用户当前运行值；运行期配置、环境变量、页面热更新和启动参数均可能覆盖。`tmp/` 数据和用户上传资料不参与生成。参数含义优先结合《软件使用文档》《软件算法调参与验证文档》及模块说明核对。",
        "",
        f"参数路径共 {len(paths)} 项（叶子字段；数组 / 映射按完整 JSON 值展示）。",
        "",
        "| 配置路径 | 代码默认值 | 总线模板值 | 分路模板值 |",
        "| --- | --- | --- | --- |",
    ]
    for path in paths:
        code_value = _json_cell(code_values[path]) if path in code_values else "无代码默认项"
        bus_value = _json_cell(bus_values[path]) if path in bus_values else "未显式配置"
        branch_value = _json_cell(branch_values[path]) if path in branch_values else "未显式配置"
        rows.append(f"| `{path}` | `{code_value}` | `{bus_value}` | `{branch_value}` |")
    rows.extend([
        "",
        "## 使用边界",
        "",
        "- 代码默认值、总线侧模板值、分路侧模板值是三类来源；界面保存、环境变量覆盖、服务启动参数和运行时热更新可能使当前有效值不同。",
        "- 模板中显示“未显式配置”只表示该模板 JSON 没有直接写出这一叶子字段；实际有效值由该侧配置加载 / 合并逻辑与代码默认值共同决定。",
        "- `NILM_TUNING_GUIDE.md` 提供负荷辨识参数的工程解释、实验步骤和验证判据；涉及保护阈值或一次 / 二次侧量纲时，必须再核对现场接线、PT/CT 和配置来源。",
        "",
    ])
    return "\n".join(rows)


def load_bundled_documents(root: Path) -> List[Dict[str, Any]]:
    """Load the complete allow-listed local corpus at assistant service startup."""
    root = Path(root).resolve()
    readme = _read_text(root, "README.md")
    report = _read_text(root, "REPORT.md")
    profile_design = _read_text(root, "设备画像提取与总线侧负荷辨识事件检测算法方案.md")
    tuning = _read_text(root, "NILM_TUNING_GUIDE.md")
    data_dictionary = _read_text(root, "NILM_DATA_DICT.md")
    assistant_manual = _read_text(root, "docs/智能问答助手说明.md")

    design_sections = _extract_markdown_sections(readme, (
        r"^## 1\.", r"^### 2\.6\b", r"^## 6\.", r"^## 8\.", r"^## 9\.",
    ))
    deployment_sections = _extract_markdown_sections(readme, (
        r"^## 0\.", r"^## 2\.", r"^### 3\.1\b", r"^## 9\.",
    ))
    design_content = "\n\n".join(part for part in (
        "# 软件设计文档（架构与算法设计）",
        "## 系统定位、代码结构与配置设计\n\n" + design_sections if design_sections else "",
        "## 稳定算法口径与工程设计记录\n\n" + report if report else "",
        "## 设备画像与总线侧负荷辨识算法方案\n\n" + profile_design if profile_design else "",
    ) if part)
    deployment_content = "\n\n".join(part for part in (
        "# 软件部署说明文档",
        "> 包含环境准备、安装、启动、Web 访问与生产流程；Windows / 现场网络条目仍以文档中的待验证标记为准。",
        deployment_sections,
    ) if part)

    docs = [
        _document(
            "builtin-software-design", "软件设计文档", "软件设计",
            "系统定位、目录与配置结构、稳定算法口径、设备画像算法设计。",
            design_content,
        ),
        _document(
            "builtin-software-usage", "软件使用文档", "软件使用",
            "完整 README 用户手册，覆盖快速开始、Web / CLI / API 使用、数据源、配置、输出与验证。",
            "# 软件使用文档\n\n" + readme if readme else "",
        ),
        _document(
            "builtin-software-deployment", "软件部署说明文档", "软件部署",
            "从快速开始到环境安装、Web 启动和生产部署的操作说明。",
            deployment_content,
        ),
        _document(
            "builtin-algorithm-tuning-validation", "软件算法调参与验证文档", "算法调参与验证",
            "完整 NILM 调参与验证手册，提供参数解释、实验步骤、回放对账、判据和常见失败排查。",
            "# 软件算法调参与验证文档\n\n" + tuning if tuning else "",
        ),
        _document(
            "builtin-platform-parameters", "平台参数清单", "平台参数",
            "总线侧与分路侧出厂 JSON 模板的完整参数路径及显式默认值。",
            _build_parameter_catalog(root),
        ),
        _document(
            "builtin-assistant-guide", "智能问答模块说明文档", "智能问答助手",
            "知识来源、检索优先级、问答模式、实验指导边界、隐私与管理员配置说明。",
            "# 智能问答模块说明文档\n\n" + assistant_manual if assistant_manual else "",
        ),
        _document(
            "builtin-data-dictionary", "NILM 数据定义与质量说明", "数据定义",
            "NILM 数据源、字段、粒度、质量与预处理规则。",
            data_dictionary,
        ),
    ]
    return docs
