from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from nicegui import app, run, ui

from core.config import load_settings
from core.utils import read_json
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question

# Initialize Settings
settings = load_settings()

# State variables
state = {
    "current_index_name": "Baseline (Clean)",
    "embeddings_path": settings.paths.embeddings_json,
    "clean_path": settings.paths.clean_json,
    "top_k": 4,
    "llm_provider": settings.llm_provider,
    "model_name": settings.model_name,
}

# Cached index
index_cache: dict[str, LocalEmbeddingIndex] = {}


def get_current_index() -> LocalEmbeddingIndex | None:
    path = state["embeddings_path"]
    if not path.exists():
        return None
    cache_key = str(path)
    if cache_key not in index_cache:
        index_cache[cache_key] = LocalEmbeddingIndex.load(settings, path)
    return index_cache[cache_key]


def get_metrics(metric_type: str) -> dict[str, Any]:
    metric_files = {
        "Baseline (Clean)": settings.paths.baseline_metrics,
        "Corrupted (Damaged)": settings.paths.corrupted_metrics,
        "Repaired (Restored)": settings.paths.repaired_metrics,
    }
    target_file = metric_files.get(metric_type, settings.paths.baseline_metrics)
    if target_file.exists():
        return read_json(target_file)
    return {}


def get_quality(quality_type: str) -> dict[str, Any]:
    quality_files = {
        "Baseline (Clean)": settings.paths.quality_dir / "baseline_quality.json",
        "Corrupted (Damaged)": settings.paths.quality_dir / "corrupted_quality.json",
        "Repaired (Restored)": settings.paths.quality_dir / "repaired_quality.json",
    }
    target_file = quality_files.get(quality_type, settings.paths.quality_dir / "baseline_quality.json")
    if target_file.exists():
        return read_json(target_file)
    return {}


# Configure Dark Mode
ui.dark_mode(True)

# 1. Top Level Header
with ui.header().classes("bg-slate-900 text-white items-center justify-between px-6 py-3 border-b border-slate-800 shadow-lg"):
    with ui.row().classes("items-center gap-3"):
        ui.icon("analytics", size="32px").classes("text-indigo-400")
        with ui.column().classes("gap-0"):
            ui.label("RAG Data Observability & Search Hub").classes("text-xl font-bold tracking-wide text-slate-100")
            ui.label("Crossref Literature Search • Data Quality • Impact Analysis").classes("text-xs text-slate-400")
    with ui.row().classes("items-center gap-4"):
        ui.chip("Python 3.12", icon="code").classes("bg-slate-800 text-slate-300 text-xs")
        ui.chip("ChromaDB + MiniLM", icon="dataset").classes("bg-indigo-950 text-indigo-300 text-xs")

# 2. Top Level Left Drawer
with ui.left_drawer(value=True).classes("bg-slate-900 border-r border-slate-800 p-4 gap-4 w-80"):
    ui.label("⚙️ Control Panel").classes("text-lg font-bold text-slate-200 border-b border-slate-800 pb-2 mb-2")

    ui.label("Dataset & Index State").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    state_select = ui.select(
        options=["Baseline (Clean)", "Corrupted (Damaged)", "Repaired (Restored)"],
        value=state["current_index_name"],
        on_change=lambda e: update_state(e.value),
    ).classes("w-full bg-slate-800 text-slate-100 rounded-lg")

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("LLM Config").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    provider_badge = ui.badge(f"Provider: {settings.llm_provider} ({settings.model_name})", color="indigo").classes("w-full py-2 text-center text-xs font-mono")

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("Top-K Retrieval").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    top_k_slider = ui.slider(min=1, max=5, value=state["top_k"]).classes("w-full")
    top_k_label = ui.label(f"Top-K Docs: {state['top_k']}").classes("text-xs text-indigo-400 font-mono")
    top_k_slider.on("change", lambda e: top_k_label.set_text(f"Top-K Docs: {e.value}"))

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("Data Health Status").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    health_container = ui.column().classes("w-full gap-2")

    def refresh_health_badges():
        health_container.clear()
        metrics = get_metrics(state["current_index_name"])
        quality = get_quality(state["current_index_name"])

        is_passed = quality.get("passed", True)
        with health_container:
            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Quality Status:").classes("text-xs text-slate-400")
                ui.badge("PASSED" if is_passed else "FAILED", color="emerald" if is_passed else "rose").classes("text-xs font-bold")

            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Hit Rate:").classes("text-xs text-slate-400")
                hit_rate = metrics.get("retrieval_hit_rate", 1.0)
                ui.label(f"{hit_rate * 100:.1f}%").classes("text-xs font-bold text-indigo-400")

            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Judge Score:").classes("text-xs text-slate-400")
                score = metrics.get("mean_judge_score", 0.0)
                ui.label(f"{score:.2f} / 5.0").classes("text-xs font-bold text-amber-400")

    refresh_health_badges()

# 3. Top Level Main Content Area
with ui.column().classes("w-full min-h-screen bg-slate-950 text-slate-100 p-6 gap-6 max-w-7xl mx-auto"):

    # Header Cards Summary
    with ui.row().classes("w-full grid grid-cols-1 md:grid-cols-4 gap-4"):
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("INDEX STATE").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            current_state_label = ui.label(state["current_index_name"]).classes("text-lg font-bold text-indigo-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("RETRIEVAL HIT RATE").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            hit_rate_card_label = ui.label("100%").classes("text-2xl font-black text-emerald-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("TOKEN F1").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            f1_card_label = ui.label("0.2858").classes("text-2xl font-black text-cyan-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("JUDGE SCORE").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            judge_card_label = ui.label("4.89 / 5.0").classes("text-2xl font-black text-amber-400 mt-1")

    def update_header_cards():
        metrics = get_metrics(state["current_index_name"])
        current_state_label.set_text(state["current_index_name"])
        hit_rate = metrics.get("retrieval_hit_rate", 1.0)
        hit_rate_card_label.set_text(f"{hit_rate * 100:.1f}%")
        hit_rate_card_label.classes(replace="text-2xl font-black mt-1 " + ("text-emerald-400" if hit_rate >= 0.9 else "text-rose-400"))
        
        f1 = metrics.get("mean_token_f1", 0.0)
        f1_card_label.set_text(f"{f1:.4f}")
        
        judge = metrics.get("mean_judge_score", 0.0)
        judge_card_label.set_text(f"{judge:.2f} / 5.0")

    update_header_cards()

    # Tabs Navigation
    with ui.tabs().classes("w-full bg-slate-900 rounded-xl border border-slate-800 p-1 text-slate-300") as tabs:
        tab_chat = ui.tab("💬 RAG Search & QA", icon="search")
        tab_comparison = ui.tab("📊 Metrics Comparison", icon="table_chart")
        tab_reports = ui.tab("📑 Observability Reports", icon="article")
        tab_data = ui.tab("📁 Data Explorer", icon="folder")

    with ui.tab_panels(tabs, value=tab_chat).classes("w-full bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl"):
        
        # TAB 1: RAG Interactive Search & QA
        with ui.tab_panel(tab_chat).classes("gap-6"):
            ui.label("Semantic Search & QA Agent").classes("text-lg font-bold text-slate-100")
            ui.label("Enter a question to search the indexed Crossref literature corpus.").classes("text-xs text-slate-400 -mt-4 mb-2")

            # Sample Query Chips
            with ui.row().classes("items-center gap-2 mb-2 flex-wrap"):
                ui.label("Sample Queries:").classes("text-xs text-slate-400 font-semibold")
                
                def set_query(text: str):
                    query_input.value = text

                ui.button("Agentic RAG", on_click=lambda: set_query("What is the main summary of paper DOI 10.1016/j.artint.2023.103901?")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")
                ui.button("List Authors", on_click=lambda: set_query("Who are the authors of the paper titled 'Agentic Retrieval-Augmented Generation'")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")
                ui.button("Publication Date", on_click=lambda: set_query("When was the paper titled 'Agentic Retrieval-Augmented Generation' published?")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")

            with ui.row().classes("w-full gap-3 items-center"):
                query_input = ui.input(placeholder="Ask a question about Crossref academic papers...").classes("flex-1 bg-slate-800 rounded-lg px-4 text-slate-100")
                search_btn = ui.button("Search", icon="search").classes("bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6 py-2 rounded-lg")

            # Results Area
            results_container = ui.column().classes("w-full gap-4 mt-4")

            async def do_search():
                q = query_input.value.strip()
                if not q:
                    ui.notify("Please enter a question.", type="warning")
                    return
                
                results_container.clear()
                with results_container:
                    spinner = ui.spinner("dots", size="lg").classes("self-center my-4 text-indigo-400")
                    ui.label("Retrieving contexts & generating response...").classes("text-xs text-slate-400 self-center")

                idx = get_current_index()
                if not idx:
                    results_container.clear()
                    with results_container:
                        ui.notify("Embedding index file not found.", type="negative")
                    return

                # Execute search
                ans_res = answer_question(q, settings=settings, index=idx, top_k=top_k_slider.value)
                raw_search_results = idx.search(q, top_k=top_k_slider.value)

                results_container.clear()
                with results_container:
                    # RAG Answer Card
                    with ui.card().classes("w-full bg-slate-850 border border-indigo-900/50 p-4 rounded-xl shadow-lg"):
                        with ui.row().classes("items-center gap-2 border-b border-slate-800 pb-2 mb-2"):
                            ui.icon("smart_toy", color="indigo").classes("text-xl")
                            ui.label("Agent Response").classes("font-bold text-indigo-300 text-sm")
                        ui.markdown(ans_res.answer).classes("text-slate-100 text-sm leading-relaxed")

                    # Context Cards Section
                    ui.label(f"Retrieved Document Contexts ({len(raw_search_results)} items)").classes("font-bold text-slate-300 text-sm mt-4")
                    
                    for res in raw_search_results:
                        meta = res.metadata
                        similarity_pct = min(100.0, res.score * 100)
                        score_color = "emerald" if similarity_pct >= 70 else "amber" if similarity_pct >= 40 else "rose"

                        with ui.card().classes("w-full bg-slate-800 border border-slate-700/60 p-4 rounded-xl gap-2 hover:border-indigo-500/50 transition-all"):
                            with ui.row().classes("w-full justify-between items-start gap-2"):
                                ui.label(res.title).classes("font-bold text-slate-100 text-base leading-snug flex-1")
                                ui.badge(f"{similarity_pct:.1f}% Match", color=score_color).classes("font-mono text-xs px-2 py-1")

                            with ui.row().classes("items-center gap-4 text-xs text-slate-400 flex-wrap"):
                                ui.label(f"DOI: {res.paper_id}").classes("font-mono text-indigo-400")
                                ui.label(f"Category: {meta.get('primary_category', 'General')}")
                                ui.label(f"Published: {meta.get('published', 'N/A')}")
                                ui.label(f"Authors: {meta.get('authors_joined', 'N/A')}")

                            ui.markdown(f"**Summary**: {meta.get('summary', '')}").classes("text-xs text-slate-300 bg-slate-850 p-3 rounded-lg border border-slate-750 mt-1")

                            if meta.get("abs_url"):
                                ui.link("🔗 View Source on Crossref", meta["abs_url"], new_tab=True).classes("text-xs text-indigo-400 hover:text-indigo-300 mt-1")

            search_btn.on("click", do_search)
            query_input.on("keydown.enter", do_search)

        # TAB 2: Metrics Comparison
        with ui.tab_panel(tab_comparison).classes("gap-6"):
            ui.label("Baseline vs Corrupted vs Repaired Comparison").classes("text-lg font-bold text-slate-100")
            ui.label("Empirical metrics measured on the same 18-question evaluation test set.").classes("text-xs text-slate-400 -mt-4 mb-4")

            b_metrics = get_metrics("Baseline (Clean)")
            c_metrics = get_metrics("Corrupted (Damaged)")
            r_metrics = get_metrics("Repaired (Restored)")

            columns = [
                {"name": "state", "label": "Pipeline State", "field": "state", "align": "left"},
                {"name": "samples", "label": "Eval Samples", "field": "samples", "align": "center"},
                {"name": "hit_rate", "label": "Retrieval Hit Rate", "field": "hit_rate", "align": "center"},
                {"name": "token_f1", "label": "Mean Token F1", "field": "token_f1", "align": "center"},
                {"name": "judge_accuracy", "label": "Judge Accuracy", "field": "judge_accuracy", "align": "center"},
                {"name": "judge_score", "label": "Mean Judge Score", "field": "judge_score", "align": "center"},
            ]

            rows = [
                {
                    "state": "Baseline (Clean)",
                    "samples": b_metrics.get("samples", 18),
                    "hit_rate": f"{b_metrics.get('retrieval_hit_rate', 1.0)*100:.1f}%",
                    "token_f1": f"{b_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{b_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{b_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
                {
                    "state": "Corrupted (Damaged)",
                    "samples": c_metrics.get("samples", 18),
                    "hit_rate": f"{c_metrics.get('retrieval_hit_rate', 0.0)*100:.1f}%",
                    "token_f1": f"{c_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{c_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{c_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
                {
                    "state": "Repaired (Restored)",
                    "samples": r_metrics.get("samples", 18),
                    "hit_rate": f"{r_metrics.get('retrieval_hit_rate', 1.0)*100:.1f}%",
                    "token_f1": f"{r_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{r_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{r_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
            ]

            ui.table(columns=columns, rows=rows, row_key="state").classes("w-full bg-slate-800 text-slate-100 rounded-xl border border-slate-700")

        # TAB 3: Observability Reports Viewer
        with ui.tab_panel(tab_reports).classes("gap-4"):
            ui.label("Data Observability & Health Reports").classes("text-lg font-bold text-slate-100")
            
            with ui.row().classes("items-center gap-4 mb-2"):
                report_select = ui.select(
                    options=["Phase 1 Baseline Report", "Corruption Comparison Report", "Corruption Log JSON"],
                    value="Corruption Comparison Report",
                ).classes("w-80 bg-slate-800 text-slate-100 rounded-lg")

            report_viewer = ui.markdown().classes("w-full bg-slate-850 border border-slate-800 p-6 rounded-xl text-slate-200 text-sm leading-relaxed font-mono")

            def load_report_content(val: str):
                report_paths = {
                    "Phase 1 Baseline Report": settings.paths.baseline_report,
                    "Corruption Comparison Report": settings.paths.comparison_report,
                    "Corruption Log JSON": settings.paths.corruption_log,
                }
                target_path = report_paths.get(val, settings.paths.comparison_report)
                if target_path.exists():
                    if target_path.suffix == ".json":
                        content = f"```json\n{target_path.read_text(encoding='utf-8')}\n```"
                    else:
                        content = target_path.read_text(encoding="utf-8")
                    report_viewer.set_content(content)
                else:
                    report_viewer.set_content("*Report file not found on disk.*")

            report_select.on("change", lambda e: load_report_content(e.value))
            load_report_content("Corruption Comparison Report")

        # TAB 4: Data Explorer
        with ui.tab_panel(tab_data).classes("gap-4"):
            ui.label("Crossref Dataset Explorer").classes("text-lg font-bold text-slate-100")
            
            def load_dataset_table():
                clean_path = state["clean_path"]
                if clean_path.exists():
                    df = pd.read_json(clean_path)
                    data_cols = [
                        {"name": "paper_id", "label": "DOI / ID", "field": "paper_id", "align": "left"},
                        {"name": "title", "label": "Title", "field": "title", "align": "left"},
                        {"name": "published", "label": "Published", "field": "published", "align": "center"},
                        {"name": "primary_category", "label": "Category", "field": "primary_category", "align": "center"},
                    ]
                    data_rows = df.to_dict(orient="records")
                    ui.table(columns=data_cols, rows=data_rows, row_key="paper_id").classes("w-full bg-slate-800 text-slate-100 rounded-xl border border-slate-700")
                else:
                    ui.label("Dataset file not found.").classes("text-rose-400")

            load_dataset_table()


def update_state(val: str):
    state["current_index_name"] = val
    path_map = {
        "Baseline (Clean)": (settings.paths.embeddings_json, settings.paths.clean_json),
        "Corrupted (Damaged)": (settings.paths.corrupted_embeddings_json, settings.paths.corrupted_clean_json),
        "Repaired (Restored)": (settings.paths.repaired_embeddings_json, settings.paths.repaired_clean_json),
    }
    emb_p, clean_p = path_map.get(val, (settings.paths.embeddings_json, settings.paths.clean_json))
    state["embeddings_path"] = emb_p
    state["clean_path"] = clean_p
    refresh_health_badges()
    update_header_cards()


# Run Application
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Day 10 - Data Observability RAG Hub",
        port=8080,
        dark=True,
        reload=False,
    )
