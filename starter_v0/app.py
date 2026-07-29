from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

ROOT = Path(__file__).parent
ARTIFACTS_DIR = ROOT / "artifacts"
RUNS_DIR = ROOT / "runs"
TRANSCRIPTS_DIR = ROOT / "transcripts"
DATA_DIR = ROOT / "data"
DEFAULT_PROVIDER = "openrouter"
VERSION_OPTIONS = ["v0", "v1", "v2", "v3"]

sys.path.insert(0, str(ROOT))

from env_loader import load_lab_env  # noqa: E402
from providers import make_provider  # noqa: E402
from tools import load_tool_declarations, to_openai_tools  # noqa: E402
from versioning import build_artifact_version, artifact_version_dict  # noqa: E402
from chat import run_model_tool_loop, trim_history, write_transcript, now_iso, safe_slug  # noqa: E402
from scripts.parse_runs import row_for  # noqa: E402

load_lab_env(ROOT)

st.set_page_config(page_title="Research Agent Eval UI", layout="wide")


# ---------- shared helpers ----------

def list_files_by_mtime(directory: Path, pattern: str) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)


def load_json(path: Path) -> dict[str, Any]:
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_pct(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def render_summary_metrics(summary: dict[str, Any]) -> None:
    cols = st.columns(4)
    cols[0].metric("Case Accuracy", fmt_pct(summary.get("case_accuracy")))
    cols[1].metric("Tool Routing Accuracy", fmt_pct(summary.get("tool_routing_accuracy")))
    cols[2].metric("Argument Accuracy", fmt_pct(summary.get("argument_accuracy")))
    cols[3].metric("Multiturn Accuracy", fmt_pct(summary.get("multiturn_accuracy")))

    provider_errors = summary.get("provider_error_cases", 0)
    measured = summary.get("measured_cases", 0)
    total = summary.get("total_cases", 0)
    gate_cols = st.columns(2)
    if provider_errors:
        gate_cols[0].error(f"provider_error_cases = {provider_errors} (metric không đáng tin cậy)")
    else:
        gate_cols[0].success("provider_error_cases = 0")
    if measured != total:
        gate_cols[1].warning(f"measured_cases ({measured}) != total_cases ({total})")
    else:
        gate_cols[1].success(f"measured_cases = total_cases = {total}")

    breakdown_cols = st.columns(2)
    with breakdown_cols[0]:
        st.caption("failure_counts")
        failure_counts = summary.get("failure_counts") or {}
        if failure_counts:
            st.bar_chart(failure_counts, horizontal=True)
        else:
            st.caption("(không có)")
    with breakdown_cols[1]:
        st.caption("observed_mismatch_counts")
        mismatch_counts = summary.get("observed_mismatch_counts") or {}
        if mismatch_counts:
            st.bar_chart(mismatch_counts, horizontal=True)
        else:
            st.caption("(không có)")


def render_eval_tool_trace(tool_results: list[dict[str, Any]]) -> None:
    if not tool_results:
        st.caption("(không gọi tool nào)")
        return
    for idx, event in enumerate(tool_results, start=1):
        result = event.get("result", {})
        is_error = isinstance(result, dict) and result.get("error")
        st.markdown(f"{'❌' if is_error else '✅'} **Step {idx}** — `{event.get('tool')}`({event.get('args')})")
        st.json(result, expanded=False)


def render_turn_trace(turn: dict[str, Any]) -> None:
    with st.chat_message("user"):
        st.write(turn.get("user", ""))
    with st.chat_message("assistant"):
        status = turn.get("status")
        if status == "provider_error":
            st.error(turn.get("error", "provider error"))
        else:
            st.write(turn.get("assistant_text") or "")
        rounds = turn.get("rounds") or []
        tool_events = turn.get("tool_events") or []
        if rounds:
            with st.expander(f"🔧 Tool trace ({len(tool_events)} tool call, {len(rounds)} round) — status={status}"):
                for round_record in rounds:
                    st.markdown(f"**Round {round_record.get('round')}**")
                    if round_record.get("assistant_text"):
                        st.caption(round_record["assistant_text"])
                    for event in round_record.get("tool_results", []):
                        result = event.get("result", {})
                        is_error = isinstance(result, dict) and result.get("error")
                        label = f"{'❌' if is_error else '✅'} `{event.get('tool')}`({event.get('args')})"
                        st.markdown(label)
                        st.json(result, expanded=False)


# ---------- tabs ----------

tab_eval, tab_chat, tab_transcripts = st.tabs(["📊 Eval Runs", "💬 Live Chat", "🗂 Transcripts"])

# ===== Tab 1: Eval Runs =====
with tab_eval:
    with st.expander("▶ Run eval mới", expanded=False):
        run_cols = st.columns(4)
        run_provider = run_cols[0].selectbox("Provider", ["openrouter", "openai", "anthropic", "gemini"], key="run_provider")
        run_version = run_cols[1].selectbox("Version", VERSION_OPTIONS, key="run_version")
        run_suite = run_cols[2].selectbox("Suite", ["base", "group", "cross", "extension"], key="run_suite")
        default_cases = "data/eval_base.json"
        run_cases = run_cols[3].text_input("Eval cases", value=default_cases, key="run_cases")

        if st.button("▶ Run eval", key="run_eval_button"):
            cmd = [
                sys.executable, str(ROOT / "run_eval.py"),
                "--provider", run_provider,
                "--version", run_version,
                "--suite", run_suite,
                "--eval-cases", run_cases,
            ]
            with st.spinner(f"Đang chạy: {' '.join(cmd)}"):
                proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
            with st.expander("Output", expanded=proc.returncode != 0):
                st.code((proc.stdout or "") + (proc.stderr or ""), language="text")
            if proc.returncode == 0:
                st.success("Run eval xong.")
                st.rerun()
            else:
                st.error(f"run_eval.py thoát với code {proc.returncode}")

    run_files = list_files_by_mtime(RUNS_DIR, "*.json")
    if not run_files:
        st.info("Chưa có run nào trong runs/. Chạy eval ở panel trên hoặc bằng CLI trước.")
    else:
        selected_run_path = st.selectbox(
            "Chọn run", run_files, format_func=lambda p: p.name, key="selected_run",
        )
        run_data = load_json(selected_run_path)

        header_cols = st.columns(4)
        header_cols[0].markdown(f"**run_id**\n\n`{run_data.get('run_id')}`")
        header_cols[1].markdown(f"**artifact_version**\n\n`{run_data.get('artifact_version')}`")
        header_cols[2].markdown(f"**provider / model**\n\n{run_data.get('provider')} / {run_data.get('model')}")
        header_cols[3].markdown(f"**suite**\n\n{run_data.get('suite')} (phase {run_data.get('phase')})")
        st.caption(
            f"prompt_hash={str(run_data.get('prompt_hash'))[:12]}  "
            f"tools_hash={str(run_data.get('tools_hash'))[:12]}  "
            f"generated_at={run_data.get('generated_at')}"
        )

        render_summary_metrics(run_data.get("summary", {}))

        st.subheader("Kết quả từng case")
        only_failed = st.checkbox("Chỉ hiện case fail", value=False)
        rows = [row_for(run_data, item) for item in run_data.get("results", [])]
        if only_failed:
            rows = [r for r in rows if not r.get("passed")]
        st.dataframe(rows, use_container_width=True)

        results_by_id = {item["id"]: item for item in run_data.get("results", [])}
        if results_by_id:
            case_id = st.selectbox("Xem chi tiết case", list(results_by_id.keys()), key="case_drilldown")
            item = results_by_id[case_id]
            detail_cols = st.columns(2)
            with detail_cols[0]:
                st.caption("input")
                case_input = item.get("input")
                if isinstance(case_input, str):
                    st.write(case_input)
                else:
                    st.json(case_input, expanded=False)
                st.caption("expect")
                st.json(item.get("expect"), expanded=False)
            with detail_cols[1]:
                st.caption("result")
                st.json(item.get("result"), expanded=True)
            st.caption("🔧 Tool trace")
            render_eval_tool_trace(item.get("tool_results") or [])

        st.subheader("So sánh nhiều version")
        compare_paths = st.multiselect(
            "Chọn các run để so sánh", run_files, format_func=lambda p: p.name, key="compare_runs",
        )
        if compare_paths:
            compare_rows = []
            for path in compare_paths:
                data = load_json(path)
                summary = data.get("summary", {})
                compare_rows.append({
                    "run": path.name,
                    "version": data.get("version"),
                    "case_accuracy": summary.get("case_accuracy"),
                    "tool_routing_accuracy": summary.get("tool_routing_accuracy"),
                    "argument_accuracy": summary.get("argument_accuracy"),
                    "multiturn_accuracy": summary.get("multiturn_accuracy"),
                })
            st.dataframe(compare_rows, use_container_width=True)
            chart_data = {row["version"]: {
                "case_accuracy": row["case_accuracy"],
                "tool_routing_accuracy": row["tool_routing_accuracy"],
                "argument_accuracy": row["argument_accuracy"],
            } for row in compare_rows}
            st.bar_chart({row["version"]: row["case_accuracy"] for row in compare_rows})

# ===== Tab 2: Live Chat =====
with tab_chat:
    st.caption(f"Provider: `{DEFAULT_PROVIDER}` (cố định)")
    default_chat_version = st.session_state.get("chat_version", "v0")
    chat_version = st.selectbox(
        "Version label", VERSION_OPTIONS,
        index=VERSION_OPTIONS.index(default_chat_version) if default_chat_version in VERSION_OPTIONS else 0,
        key="chat_version_input",
    )

    if "chat_transcript" not in st.session_state or st.button("🆕 New session"):
        system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        tools_path = ARTIFACTS_DIR / "tools.yaml"
        artifact_version = build_artifact_version(chat_version, system_prompt_path, tools_path)
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S%f")
        transcript_id = "_".join([safe_slug(chat_version), safe_slug(DEFAULT_PROVIDER), timestamp])
        st.session_state.chat_version = chat_version
        st.session_state.chat_transcript_path = TRANSCRIPTS_DIR / f"{transcript_id}.transcript.json"
        st.session_state.chat_transcript = {
            "transcript_id": transcript_id,
            **artifact_version_dict(artifact_version),
            "provider": DEFAULT_PROVIDER,
            "model": None,
            "system_prompt": str(system_prompt_path),
            "tools": str(tools_path),
            "history_window": 5,
            "max_tool_rounds": 4,
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "turns": [],
        }
        st.session_state.chat_history = []
        st.session_state.chat_turn_index = 0

    transcript = st.session_state.chat_transcript
    info_cols = st.columns(4)
    info_cols[0].markdown(f"**transcript_id**\n\n`{transcript['transcript_id']}`")
    info_cols[1].markdown(f"**artifact_version**\n\n`{transcript['artifact_version']}`")
    info_cols[2].markdown(f"**prompt_hash**\n\n`{transcript['prompt_hash'][:12]}`")
    info_cols[3].markdown(f"**tools_hash**\n\n`{transcript['tools_hash'][:12]}`")

    for turn in transcript["turns"]:
        render_turn_trace(turn)

    user_text = st.chat_input("Hỏi agent...")
    if user_text:
        system_prompt_path = ARTIFACTS_DIR / "system_prompt.md"
        tools_path = ARTIFACTS_DIR / "tools.yaml"
        system_prompt_text = system_prompt_path.read_text(encoding="utf-8")
        tool_declarations = load_tool_declarations(tools_path)
        openai_tools = to_openai_tools(tool_declarations)

        messages = [
            {"role": "system", "content": system_prompt_text},
            *trim_history(st.session_state.chat_history, transcript["history_window"]),
            {"role": "user", "content": user_text},
        ]

        st.session_state.chat_turn_index += 1
        turn_record: dict[str, Any] = {
            "turn_index": st.session_state.chat_turn_index,
            "started_at": now_iso(),
            "user": user_text,
            "status": "started",
            "assistant_text": None,
            "rounds": [],
            "tool_events": [],
        }

        try:
            provider = make_provider(DEFAULT_PROVIDER)
            with st.spinner("Đang gọi agent..."):
                result = run_model_tool_loop(
                    provider=provider,
                    messages=messages,
                    tools=openai_tools,
                    model=transcript.get("model"),
                    max_tool_rounds=transcript["max_tool_rounds"],
                )
            turn_record.update(result)
            assistant_text = result["assistant_text"]
            st.session_state.chat_history.append({"role": "user", "content": user_text})
            st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})
        except Exception as exc:
            turn_record.update({
                "status": "provider_error",
                "error": f"{type(exc).__name__}: {exc}",
            })

        turn_record["ended_at"] = now_iso()
        transcript["turns"].append(turn_record)
        write_transcript(st.session_state.chat_transcript_path, transcript)
        st.rerun()

    if transcript["turns"]:
        import json
        st.download_button(
            "⬇️ Download transcript JSON",
            data=json.dumps(transcript, ensure_ascii=False, indent=2, default=str),
            file_name=f"{transcript['transcript_id']}.transcript.json",
            mime="application/json",
        )

# ===== Tab 3: Transcripts =====
with tab_transcripts:
    transcript_files = list_files_by_mtime(TRANSCRIPTS_DIR, "*.transcript.json")
    if not transcript_files:
        st.info("Chưa có transcript nào trong transcripts/. Chat ở tab Live Chat trước.")
    else:
        selected = st.multiselect(
            "Chọn transcript để xem / so sánh", transcript_files, format_func=lambda p: p.name, key="selected_transcripts",
        )
        if selected:
            cols = st.columns(len(selected))
            for col, path in zip(cols, selected):
                with col:
                    data = load_json(path)
                    st.markdown(f"**{path.name}**")
                    st.caption(
                        f"version={data.get('version')}  artifact_version={data.get('artifact_version')}  "
                        f"provider={data.get('provider')}  model={data.get('model')}  created_at={data.get('created_at')}"
                    )
                    for turn in data.get("turns", []):
                        render_turn_trace(turn)
