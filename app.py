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

# Khởi tạo Settings
settings = load_settings()

# Biến trạng thái toàn cục
state = {
    "current_index_name": "Baseline (Dữ liệu sạch)",
    "embeddings_path": settings.paths.embeddings_json,
    "clean_path": settings.paths.clean_json,
    "top_k": 4,
    "selected_model_option": "Ollama: qwen2.5 (Local Đa Ngôn Ngữ)",
}

# Cache index vector
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
        "Baseline (Dữ liệu sạch)": settings.paths.baseline_metrics,
        "Corrupted (Dữ liệu lỗi)": settings.paths.corrupted_metrics,
        "Repaired (Đã phục hồi)": settings.paths.repaired_metrics,
    }
    target_file = metric_files.get(metric_type, settings.paths.baseline_metrics)
    if target_file.exists():
        return read_json(target_file)
    return {}


def get_quality(quality_type: str) -> dict[str, Any]:
    quality_files = {
        "Baseline (Dữ liệu sạch)": settings.paths.quality_dir / "baseline_quality.json",
        "Corrupted (Dữ liệu lỗi)": settings.paths.quality_dir / "corrupted_quality.json",
        "Repaired (Đã phục hồi)": settings.paths.quality_dir / "repaired_quality.json",
    }
    target_file = quality_files.get(quality_type, settings.paths.quality_dir / "baseline_quality.json")
    if target_file.exists():
        return read_json(target_file)
    return {}



# Cấu hình Dark Mode
ui.dark_mode(True)

# 1. Header trên cùng (Top Level Header)
with ui.header().classes("bg-slate-900 text-white items-center justify-between px-6 py-3 border-b border-slate-800 shadow-lg"):
    with ui.row().classes("items-center gap-3"):
        ui.icon("analytics", size="32px").classes("text-indigo-400")
        with ui.column().classes("gap-0"):
            ui.label("Hệ Thống Quan Sát Dữ Liệu RAG & Tìm Kiếm Bài Báo Crossref").classes("text-xl font-bold tracking-wide text-slate-100")
            ui.label("Tra cứu ngữ nghĩa • Qwen2.5 Đa ngôn ngữ • Giám sát chất lượng & độ tươi dữ liệu").classes("text-xs text-slate-400")
    with ui.row().classes("items-center gap-4"):
        ui.chip("Python 3.12", icon="code").classes("bg-slate-800 text-slate-300 text-xs")
        ui.chip("ChromaDB + MiniLM", icon="dataset").classes("bg-indigo-950 text-indigo-300 text-xs")

# 2. Bảng điều khiển bên trái (Top Level Left Drawer)
with ui.left_drawer(value=True).classes("bg-slate-900 border-r border-slate-800 p-4 gap-4 w-80"):
    ui.label("⚙️ Bảng Điều Khiển").classes("text-lg font-bold text-slate-200 border-b border-slate-800 pb-2 mb-2")

    ui.label("Trạng Thái Dữ Liệu & Index").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    state_select = ui.select(
        options=["Baseline (Dữ liệu sạch)", "Corrupted (Dữ liệu lỗi)", "Repaired (Đã phục hồi)"],
        value=state["current_index_name"],
        on_change=lambda e: update_state(e.value),
    ).classes("w-full bg-slate-800 text-slate-100 rounded-lg")

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("Cấu Hình Mô Hình LLM").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    model_select = ui.select(
        options=[
            "Ollama: qwen2.5 (Local Đa Ngôn Ngữ)",
            "OpenAI: gpt-4o-mini (Cloud API)",
        ],
        value=state["selected_model_option"],
        on_change=lambda e: update_model(e.value),
    ).classes("w-full bg-slate-800 text-slate-100 rounded-lg")

    provider_badge = ui.badge(f"LLM: {settings.llm_provider} ({settings.model_name})", color="indigo").classes("w-full py-2 text-center text-xs font-mono mt-1")

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("Số Tài Liệu Truy Vấn (Top-K)").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    top_k_slider = ui.slider(min=1, max=5, value=state["top_k"]).classes("w-full")
    top_k_label = ui.label(f"Top-K Tài Liệu: {state['top_k']}").classes("text-xs text-indigo-400 font-mono")
    top_k_slider.on("change", lambda e: top_k_label.set_text(f"Top-K Tài Liệu: {e.value}"))

    ui.separator().classes("bg-slate-800 my-2")

    ui.label("Sức Khỏe Dữ Liệu (Health)").classes("text-xs font-semibold uppercase text-slate-400 tracking-wider")
    health_container = ui.column().classes("w-full gap-2")

    def refresh_health_badges():
        health_container.clear()
        metrics = get_metrics(state["current_index_name"])
        quality = get_quality(state["current_index_name"])

        is_passed = quality.get("passed", True)
        with health_container:
            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Chất lượng (Quality):").classes("text-xs text-slate-400")
                ui.badge("ĐẠT (PASSED)" if is_passed else "LỖI (FAILED)", color="emerald" if is_passed else "rose").classes("text-xs font-bold")

            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Tỷ lệ Hit Rate:").classes("text-xs text-slate-400")
                hit_rate = metrics.get("retrieval_hit_rate", 1.0)
                ui.label(f"{hit_rate * 100:.1f}%").classes("text-xs font-bold text-indigo-400")

            with ui.row().classes("w-full justify-between items-center bg-slate-850 p-2 rounded border border-slate-800"):
                ui.label("Điểm LLM Judge:").classes("text-xs text-slate-400")
                score = metrics.get("mean_judge_score", 0.0)
                ui.label(f"{score:.2f} / 5.0").classes("text-xs font-bold text-amber-400")

    refresh_health_badges()

# 3. Khu vực nội dung chính (Top Level Main Content Area)
with ui.column().classes("w-full min-h-screen bg-slate-950 text-slate-100 p-6 gap-6 max-w-7xl mx-auto"):

    # Thẻ tóm tắt chỉ số tổng quan trên cùng
    with ui.row().classes("w-full grid grid-cols-1 md:grid-cols-4 gap-4"):
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("TRẠNG THÁI INDEX").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            current_state_label = ui.label(state["current_index_name"]).classes("text-base font-bold text-indigo-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("TỶ LỆ HIT RATE").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            hit_rate_card_label = ui.label("100%").classes("text-2xl font-black text-emerald-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("ĐIỂM TOKEN F1").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
            f1_card_label = ui.label("0.2858").classes("text-2xl font-black text-cyan-400 mt-1")
        
        with ui.card().classes("bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-md"):
            ui.label("ĐIỂM LLM JUDGE").classes("text-xs font-bold text-slate-400 uppercase tracking-wider")
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

    # Các Tab Chức Năng
    with ui.tabs().classes("w-full bg-slate-900 rounded-xl border border-slate-800 p-1 text-slate-300") as tabs:
        tab_chat = ui.tab("💬 Tìm Kiếm & Hỏi Đáp RAG", icon="search")
        tab_comparison = ui.tab("📊 So Sánh Chỉ Số Thực Nghiệm", icon="table_chart")
        tab_reports = ui.tab("📑 Báo Cáo Quan Sát Dữ Liệu", icon="article")
        tab_data = ui.tab("📁 Duyệt Dataset Bài Báo", icon="folder")

    with ui.tab_panels(tabs, value=tab_chat).classes("w-full bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl"):
        
        # TAB 1: Tìm Kiếm & Hỏi Đáp RAG
        with ui.tab_panel(tab_chat).classes("gap-6"):
            ui.label("Trợ Lý Tìm Kiếm Ngữ Nghĩa & Hỏi Đáp Bài Báo (Hỗ Trợ Tiếng Việt - Qwen2.5)").classes("text-lg font-bold text-slate-100")
            ui.label("Nhập câu hỏi bằng Tiếng Việt hoặc Tiếng Anh để tra cứu thông tin bài báo học thuật Crossref.").classes("text-xs text-slate-400 -mt-4 mb-2")

            # Gợi ý câu hỏi mẫu
            with ui.row().classes("items-center gap-2 mb-2 flex-wrap"):
                ui.label("Câu hỏi mẫu:").classes("text-xs text-slate-400 font-semibold")
                
                def set_query(text: str):
                    query_input.value = text

                ui.button("Tóm tắt Agentic RAG (Tiếng Việt)", on_click=lambda: set_query("Hãy tóm tắt nội dung chính của bài báo về Agentic Retrieval-Augmented Generation bằng Tiếng Việt")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")
                ui.button("Danh sách Tác giả", on_click=lambda: set_query("Ai là tác giả của bài báo có tiêu đề 'Agentic Retrieval-Augmented Generation'")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")
                ui.button("Ngày Xuất bản", on_click=lambda: set_query("Bài báo có tiêu đề 'Agentic Retrieval-Augmented Generation' được xuất bản vào ngày nào?")).classes("text-xs bg-slate-800 hover:bg-indigo-900 text-slate-300 rounded-full px-3 py-1")

            with ui.row().classes("w-full gap-3 items-center"):
                query_input = ui.input(placeholder="Nhập câu hỏi tra cứu về các bài báo học thuật (Tiếng Việt hoặc Tiếng Anh)...").classes("flex-1 bg-slate-800 rounded-lg px-4 text-slate-100")
                search_btn = ui.button("Tìm Kiếm", icon="search").classes("bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6 py-2 rounded-lg")

            # Khu vực hiển thị kết quả
            results_container = ui.column().classes("w-full gap-4 mt-4")

            async def do_search():
                q = query_input.value.strip()
                if not q:
                    ui.notify("Vui lòng nhập câu hỏi tra cứu.", type="warning")
                    return
                
                results_container.clear()
                with results_container:
                    spinner = ui.spinner("dots", size="lg").classes("self-center my-4 text-indigo-400")
                    ui.label("Đang truy vấn ngữ cảnh & tạo câu trả lời với Qwen2.5...").classes("text-xs text-slate-400 self-center")

                idx = get_current_index()
                if not idx:
                    results_container.clear()
                    with results_container:
                        ui.notify("Không tìm thấy file index vector.", type="negative")
                    return

                # Thực hiện truy vấn
                ans_res = answer_question(q, settings=settings, index=idx, top_k=top_k_slider.value)
                raw_search_results = idx.search(q, top_k=top_k_slider.value)

                results_container.clear()
                with results_container:
                    # Thẻ Câu Trả Lời RAG
                    with ui.card().classes("w-full bg-slate-850 border border-indigo-900/50 p-4 rounded-xl shadow-lg"):
                        with ui.row().classes("items-center justify-between border-b border-slate-800 pb-2 mb-2"):
                            with ui.row().classes("items-center gap-2"):
                                ui.icon("smart_toy", color="indigo").classes("text-xl")
                                ui.label(f"🤖 Câu Trả Lời Của RAG Agent ({settings.model_name})").classes("font-bold text-indigo-300 text-sm")
                            ui.chip(settings.llm_provider, color="indigo").classes("text-xs font-mono")
                        ui.markdown(ans_res.answer).classes("text-slate-100 text-sm leading-relaxed")

                    # Các Thẻ Tài Liệu Ngữ Cảnh (Retrieved Context Cards)
                    ui.label(f"Tài Liệu Ngữ Cảnh Tìm Được ({len(raw_search_results)} tài liệu)").classes("font-bold text-slate-300 text-sm mt-4")
                    
                    for res in raw_search_results:
                        meta = res.metadata
                        similarity_pct = min(100.0, res.score * 100)
                        score_color = "emerald" if similarity_pct >= 70 else "amber" if similarity_pct >= 40 else "rose"

                        with ui.card().classes("w-full bg-slate-800 border border-slate-700/60 p-4 rounded-xl gap-2 hover:border-indigo-500/50 transition-all"):
                            with ui.row().classes("w-full justify-between items-start gap-2"):
                                ui.label(res.title).classes("font-bold text-slate-100 text-base leading-snug flex-1")
                                ui.badge(f"{similarity_pct:.1f}% Khớp Ngữ Nghĩa", color=score_color).classes("font-mono text-xs px-2 py-1")

                            with ui.row().classes("items-center gap-4 text-xs text-slate-400 flex-wrap"):
                                ui.label(f"Mã DOI: {res.paper_id}").classes("font-mono text-indigo-400")
                                ui.label(f"Chuyên mục: {meta.get('primary_category', 'Chung')}")
                                ui.label(f"Ngày xuất bản: {meta.get('published', 'Không rõ')}")
                                ui.label(f"Tác giả: {meta.get('authors_joined', 'Không rõ')}")

                            ui.markdown(f"**Tóm tắt (Abstract)**: {meta.get('summary', '')}").classes("text-xs text-slate-300 bg-slate-850 p-3 rounded-lg border border-slate-750 mt-1")

                            if meta.get("abs_url"):
                                ui.link("🔗 Xem bài báo gốc trên Crossref", meta["abs_url"], new_tab=True).classes("text-xs text-indigo-400 hover:text-indigo-300 mt-1")

            search_btn.on("click", do_search)
            query_input.on("keydown.enter", do_search)

        # TAB 2: So Sánh Chỉ Số Thực Nghiệm
        with ui.tab_panel(tab_comparison).classes("gap-6"):
            ui.label("Bảng So Sánh Hiệu Năng: Baseline vs Corrupted vs Repaired").classes("text-lg font-bold text-slate-100")
            ui.label("Chỉ số đo đạc thực tế trên cùng một bộ câu hỏi đánh giá (18 câu hỏi).").classes("text-xs text-slate-400 -mt-4 mb-4")

            b_metrics = get_metrics("Baseline (Dữ liệu sạch)")
            c_metrics = get_metrics("Corrupted (Dữ liệu lỗi)")
            r_metrics = get_metrics("Repaired (Đã phục hồi)")

            columns = [
                {"name": "state", "label": "Trạng thái Pipeline", "field": "state", "align": "left"},
                {"name": "samples", "label": "Số câu hỏi Eval", "field": "samples", "align": "center"},
                {"name": "hit_rate", "label": "Retrieval Hit Rate", "field": "hit_rate", "align": "center"},
                {"name": "token_f1", "label": "Mean Token F1", "field": "token_f1", "align": "center"},
                {"name": "judge_accuracy", "label": "Độ chính xác Judge", "field": "judge_accuracy", "align": "center"},
                {"name": "judge_score", "label": "Điểm Judge trung bình", "field": "judge_score", "align": "center"},
            ]

            rows = [
                {
                    "state": "Baseline (Dữ liệu sạch)",
                    "samples": b_metrics.get("samples", 18),
                    "hit_rate": f"{b_metrics.get('retrieval_hit_rate', 1.0)*100:.1f}%",
                    "token_f1": f"{b_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{b_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{b_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
                {
                    "state": "Corrupted (Dữ liệu lỗi)",
                    "samples": c_metrics.get("samples", 18),
                    "hit_rate": f"{c_metrics.get('retrieval_hit_rate', 0.0)*100:.1f}%",
                    "token_f1": f"{c_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{c_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{c_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
                {
                    "state": "Repaired (Đã phục hồi)",
                    "samples": r_metrics.get("samples", 18),
                    "hit_rate": f"{r_metrics.get('retrieval_hit_rate', 1.0)*100:.1f}%",
                    "token_f1": f"{r_metrics.get('mean_token_f1', 0.0):.4f}",
                    "judge_accuracy": f"{r_metrics.get('judge_accuracy', 0.0)*100:.1f}%",
                    "judge_score": f"{r_metrics.get('mean_judge_score', 0.0):.2f} / 5.0",
                },
            ]

            ui.table(columns=columns, rows=rows, row_key="state").classes("w-full bg-slate-800 text-slate-100 rounded-xl border border-slate-700")

        # TAB 3: Báo Cáo Quan Sát Dữ Liệu
        with ui.tab_panel(tab_reports).classes("gap-4"):
            ui.label("Báo Cáo Sức Khỏe Dữ Liệu & Nhật Ký Lỗi").classes("text-lg font-bold text-slate-100")
            
            with ui.row().classes("items-center gap-4 mb-2"):
                report_select = ui.select(
                    options=["Báo Cáo Pha 1 (Baseline)", "Báo Cáo So Sánh Corruption", "Nhật Ký Làm Hỏng Dữ Liệu (JSON)"],
                    value="Báo Cáo So Sánh Corruption",
                ).classes("w-80 bg-slate-800 text-slate-100 rounded-lg")

            report_viewer = ui.markdown().classes("w-full bg-slate-850 border border-slate-800 p-6 rounded-xl text-slate-200 text-sm leading-relaxed font-mono")

            def load_report_content(val: str):
                report_paths = {
                    "Báo Cáo Pha 1 (Baseline)": settings.paths.baseline_report,
                    "Báo Cáo So Sánh Corruption": settings.paths.comparison_report,
                    "Nhật Ký Làm Hỏng Dữ Liệu (JSON)": settings.paths.corruption_log,
                }
                target_path = report_paths.get(val, settings.paths.comparison_report)
                if target_path.exists():
                    if target_path.suffix == ".json":
                        content = f"```json\n{target_path.read_text(encoding='utf-8')}\n```"
                    else:
                        content = target_path.read_text(encoding="utf-8")
                    report_viewer.set_content(content)
                else:
                    report_viewer.set_content("*Không tìm thấy file báo cáo trên đĩa.*")

            report_select.on("change", lambda e: load_report_content(e.value))
            load_report_content("Báo Cáo So Sánh Corruption")

        # TAB 4: Duyệt Dataset
        with ui.tab_panel(tab_data).classes("gap-4"):
            ui.label("Duyệt Dữ Liệu Bài Báo Crossref").classes("text-lg font-bold text-slate-100")
            
            def load_dataset_table():
                clean_path = state["clean_path"]
                if clean_path.exists():
                    df = pd.read_json(clean_path)
                    data_cols = [
                        {"name": "paper_id", "label": "Mã DOI / ID", "field": "paper_id", "align": "left"},
                        {"name": "title", "label": "Tiêu đề bài báo", "field": "title", "align": "left"},
                        {"name": "published", "label": "Ngày xuất bản", "field": "published", "align": "center"},
                        {"name": "primary_category", "label": "Chuyên mục", "field": "primary_category", "align": "center"},
                    ]
                    data_rows = df.to_dict(orient="records")
                    ui.table(columns=data_cols, rows=data_rows, row_key="paper_id").classes("w-full bg-slate-800 text-slate-100 rounded-xl border border-slate-700")
                else:
                    ui.label("Không tìm thấy file dataset.").classes("text-rose-400")

            load_dataset_table()


def update_state(val: str):
    state["current_index_name"] = val
    path_map = {
        "Baseline (Dữ liệu sạch)": (settings.paths.embeddings_json, settings.paths.clean_json),
        "Corrupted (Dữ liệu lỗi)": (settings.paths.corrupted_embeddings_json, settings.paths.corrupted_clean_json),
        "Repaired (Đã phục hồi)": (settings.paths.repaired_embeddings_json, settings.paths.repaired_clean_json),
    }
    emb_p, clean_p = path_map.get(val, (settings.paths.embeddings_json, settings.paths.clean_json))
    state["embeddings_path"] = emb_p
    state["clean_path"] = clean_p
    refresh_health_badges()
    update_header_cards()


def update_model(val: str):
    state["selected_model_option"] = val
    if "qwen2.5" in val:
        settings.llm_provider = "ollama"
        settings.model_name = "qwen2.5"
    elif "gpt-4o-mini" in val:
        settings.llm_provider = "openai"
        settings.model_name = "gpt-4o-mini"
    
    provider_badge.set_text(f"LLM: {settings.llm_provider} ({settings.model_name})")
    ui.notify(f"Đã chuyển mô hình LLM sang: {settings.llm_provider} ({settings.model_name})", type="positive")


# Chạy Ứng Dụng
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title="Day 10 - Data Observability RAG Hub (Qwen2.5)",
        port=8080,
        dark=True,
        reload=False,
    )
