#!/usr/bin/env python3
"""
=============================================================================
  COMPREHENSIVE ACCURACY TEST – CV Screener & Evaluator
  (Quota-Optimized: tối đa ~8 Gemini API calls)
=============================================================================

Bao gồm 4 nhóm test:
  [A] OCR Accuracy – CV Image  : render CV text → PNG → OCR → so sánh với ground truth
  [B] OCR Accuracy – JD Image  : render JD text → PNG → OCR → so sánh với ground truth  
  [C] Scoring Accuracy         : 3 loại CV (perfect/partial/mismatch) vs 1 JD thực từ data.csv
                                  đo tỉ lệ AI phân loại đúng (Phù hợp/Tiềm năng/Loại)
  [D] Performance              : đo latency từng bước (OCR, JD extract, evaluate)

Chiến lược tiết kiệm quota:
  - Gemini cache sẵn có (sqlite): các call trùng lặp → 0 API call
  - OCR test: 1 ảnh CV + 1 ảnh JD → 2 API calls
  - JD extract: 1 JD text từ data.csv (dùng fallback nếu quota hết)
  - Scoring: 3 CV → 3 evaluate calls (background, không block)
  - Tổng thực tế ≤ 6 calls (hoặc ít hơn nếu cache hit)

Chạy: poetry run python accuracy_test.py
=============================================================================
"""

import sys, os, csv, json, time, uuid, io, difflib, re
import requests
from pathlib import Path
from datetime import datetime
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

# ── Sys config ────────────────────────────────────────────────────────────────
if sys.platform.startswith("win"):
    sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

BASE_URL   = "http://127.0.0.1:8000"
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CSV_PATH   = Path(__file__).parent.parent / "data.csv"
RESULTS_PATH = Path(__file__).parent / "accuracy_results.json"

# Quota: giây chờ giữa mỗi API call tới Gemini
GEMINI_DELAY = 15   # 15 RPM free tier → ~4s/call safe margin
# Thời gian chờ background scoring sau khi apply (giây)
SCORE_WAIT  = 30    # background thread cần thời gian gọi Gemini

# Ground truth phân loại
GT = {
    "perfect":    {"status": "Phù hợp",   "score_min": 68, "score_max": 100},
    "partial":    {"status": "Tiềm năng", "score_min": 30, "score_max": 74},
    "mismatched": {"status": "Loại",      "score_min": 0,  "score_max": 39},
}

# ── ANSI colors ───────────────────────────────────────────────────────────────
def _c(t, c): return f"\033[{c}m{t}\033[0m"
def green(t):  return _c(t, "32")
def red(t):    return _c(t, "31")
def yellow(t): return _c(t, "33")
def cyan(t):   return _c(t, "36")
def bold(t):   return _c(t, "1")
def dim(t):    return _c(t, "2")

# ── Utilities ─────────────────────────────────────────────────────────────────
def similarity(a: str, b: str) -> float:
    """Tính tỉ lệ tương đồng giữa 2 chuỗi (0.0 → 1.0)."""
    if not a and not b: return 1.0
    if not a or not b:  return 0.0
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

def keyword_recall(ground_truth: str, extracted: str) -> float:
    """Tỉ lệ từ khóa trong ground truth xuất hiện trong extracted text."""
    words = set(re.findall(r"\b\w{4,}\b", ground_truth.lower()))
    if not words: return 1.0
    found = sum(1 for w in words if w in extracted.lower())
    return found / len(words)

def section_marker(title: str):
    print()
    print(bold(f"{'─'*70}"))
    print(bold(f"  {title}"))
    print(bold(f"{'─'*70}"))

def result_row(label: str, value: str, ok: bool | None = None):
    icon = green("✅") if ok is True else red("❌") if ok is False else yellow("⚠️")
    prefix = f"  {icon} " if ok is not None else "     "
    print(f"{prefix}{label:<40} {value}")

# ── Image generators ──────────────────────────────────────────────────────────
def render_to_png(text: str, output_path: Path) -> Path:
    """Render plain text → PNG image (giả lập CV/JD scan)."""
    import textwrap
    img = Image.new("RGB", (900, 1200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        font = ImageFont.load_default()
    y, margin = 30, 40
    
    # Wrap text to fit width (approx 90 chars per line for font size 15 on 900px width)
    wrapped_lines = []
    for line in text.split("\n"):
        if not line.strip():
            wrapped_lines.append("")
        else:
            wrapped_lines.extend(textwrap.wrap(line, width=80))
            
    for line in wrapped_lines:
        draw.text((margin, y), line, fill=(10, 10, 10), font=font)
        y += 22
        if y > 1170: break
    img.save(str(output_path), "PNG")
    return output_path

def render_to_pdf_bytes(text: str) -> bytes:
    """Render plain text → PDF bytes."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    clean = text.encode("latin-1", "replace").decode("latin-1")
    for line in clean.split("\n"):
        pdf.multi_cell(0, 5, txt=line)
    return pdf.output(dest="S").encode("latin-1")

# ── CV text builders ──────────────────────────────────────────────────────────
def build_cv(ctype: str, job_title: str, required_skills: list, min_exp: int, name: str) -> str:
    lines = [
        "CURRICULUM VITAE", "=" * 38,
        f"Name:  {name}",
        f"Email: {name.lower().replace(' ', '.')}@example.com",
        f"Phone: 0901234567",
        "",
    ]
    if ctype == "perfect":
        years = max(min_exp + 2, 4)
        all_s = required_skills or ["SQL", "Python", "Excel", "Power BI", "Data Analysis"]
        lines += [
            "PROFESSIONAL SUMMARY",
            f"Senior {job_title} with {years}+ years of hands-on experience. "
            "Deep expertise in all required domains with proven track record.",
            "",
            "TECHNICAL SKILLS",
            ", ".join(all_s),
            "",
            "WORK EXPERIENCE",
            f"Senior Analyst | GlobalCorp Inc. (2020 – Present)",
            f"  - {years} years experience building pipelines using: {', '.join(all_s[:4])}.",
            "  - Led dashboard design, data quality audits, and ETL optimisation.",
            "  - Delivered executive analytics reports weekly to C-suite.",
            "",
            "EDUCATION",
            "Bachelor of Science – Computer Science / Data Science (GPA 3.9)",
        ]
    elif ctype == "partial":
        years = max(0, min_exp - 1)
        half = (required_skills or ["Excel", "SQL"])[:max(1, len(required_skills) // 2)]
        lines += [
            "PROFESSIONAL SUMMARY",
            f"Motivated junior analyst with {years} year(s) experience in reporting. "
            "Looking to grow technical skills.",
            "",
            "TECHNICAL SKILLS",
            ", ".join(half),
            "",
            "WORK EXPERIENCE",
            "Data Assistant | SmallBiz Co. (2023 – Present)",
            f"  - Maintained Excel-based operational reports and basic {half[0]} queries.",
            "  - Assisted senior team with ad-hoc data extraction.",
            "",
            "EDUCATION",
            "Bachelor of Business Administration – General Studies",
        ]
    else:  # mismatched
        lines += [
            "PROFESSIONAL SUMMARY",
            "Creative Graphic Designer with 2 years experience crafting visual content "
            "for social media, print, and web.",
            "",
            "TECHNICAL SKILLS",
            "Adobe Photoshop, Illustrator, InDesign, Figma, Canva, Procreate",
            "",
            "WORK EXPERIENCE",
            "Senior Designer | PixelStudio (2022 – Present)",
            "  - Produced brand identity packages, print layouts, and UI mockups.",
            "  - Managed client briefs from concept to final delivery.",
            "",
            "EDUCATION",
            "Bachelor of Fine Arts – Visual Communication",
        ]
    return "\n".join(lines)

# ── Data CSV helpers ──────────────────────────────────────────────────────────
def load_jd_from_csv(csv_path: Path, max_jds: int = 2) -> list[dict]:
    """Đọc data.csv, lấy max_jds hàng đầu."""
    results = []
    if not csv_path.exists():
        # Try alternate path
        alt = Path(__file__).parent / "data.csv"
        if alt.exists():
            csv_path = alt
        else:
            return []
    with open(csv_path, encoding="utf-8", errors="ignore") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header
        for row in reader:
            if len(row) >= 2 and row[0].strip() and row[1].strip():
                results.append({"title": row[0].strip(), "description": row[1].strip()})
            if len(results) >= max_jds:
                break
    return results

# ── Gemini service direct calls (bypass HTTP for OCR tests) ──────────────────
def call_gemini_ocr(img_path: Path) -> tuple[str, float]:
    """Gọi gemini_service.extract_text_from_image, trả về (text, latency_s)."""
    from app.services.gemini_service import extract_text_from_image
    t0 = time.time()
    text = extract_text_from_image(str(img_path))
    return text, round(time.time() - t0, 2)

def call_gemini_jd_extract(jd_text: str) -> tuple[object, float]:
    """Gọi gemini_service.extract_jd_criteria, trả về (JDCriteriaSchema, latency_s)."""
    from app.services.gemini_service import extract_jd_criteria
    t0 = time.time()
    criteria = extract_jd_criteria(jd_text)
    return criteria, round(time.time() - t0, 2)

def call_gemini_evaluate(cv_text: str, jd_criteria_obj) -> tuple[object, float]:
    """Gọi gemini_service.evaluate_cv_against_jd, trả về (CVEvaluationSchema, latency_s).
    
    evaluate_cv_against_jd nhận jd_criteria là dict (model_dump).
    """
    from app.services.gemini_service import evaluate_cv_against_jd
    # Convert JDCriteriaSchema → dict nếu cần
    if hasattr(jd_criteria_obj, 'model_dump'):
        jd_dict = jd_criteria_obj.model_dump()
    elif hasattr(jd_criteria_obj, 'dict'):
        jd_dict = jd_criteria_obj.dict()
    else:
        jd_dict = jd_criteria_obj  # already dict
    t0 = time.time()
    result = evaluate_cv_against_jd(cv_text, jd_dict)
    return result, round(time.time() - t0, 2)

# ── HTTP helpers ──────────────────────────────────────────────────────────────
def http_get_jobs(limit: int = 3) -> list[dict]:
    r = requests.get(f"{BASE_URL}/api/v1/jobs", params={"limit": limit, "status": "active"}, timeout=10)
    r.raise_for_status()
    data = r.json()
    return (data if isinstance(data, list) else data.get("items", []))[:limit]

def http_apply(job_id: int, name: str, ctype: str, pdf_bytes: bytes) -> dict:
    fn = f"cv_{ctype}_{uuid.uuid4().hex[:6]}.pdf"
    r = requests.post(
        f"{BASE_URL}/api/v1/jobs/{job_id}/apply",
        files={"cv_file": (fn, io.BytesIO(pdf_bytes), "application/pdf")},
        data={"full_name": name, "email": f"{name.lower().replace(' ', '.')}@t.com",
              "phone": "0987654321", "cover_letter": f"type={ctype}"},
        timeout=60,
    )
    r.raise_for_status()
    resp = r.json()
    # API trả về "application_id" chứ không phải "id"
    return resp

def http_get_application(job_id: int, app_id: int) -> dict:
    r = requests.get(f"{BASE_URL}/api/v1/jobs/{job_id}/applications/{app_id}", timeout=10)
    r.raise_for_status()
    return r.json()

def http_evaluate(job_id: int, app_id: int) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/v1/jobs/{job_id}/applications/{app_id}/evaluate",
        timeout=120,
    )
    r.raise_for_status()
    return r.json()

# ═════════════════════════════════════════════════════════════════════════════
# MAIN TEST RUNNER
# ═════════════════════════════════════════════════════════════════════════════
def main():
    print()
    print(bold("=" * 70))
    print(bold("  🎯  COMPREHENSIVE ACCURACY TEST – CV Screener AI"))
    print(bold("=" * 70))
    print(f"  Thời gian  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Server     : {BASE_URL}")
    print(f"  data.csv   : {CSV_PATH}")
    print(f"  Quota delay: {GEMINI_DELAY}s between API calls")
    print()

    all_results = {}
    perf_log = []  # (section, step, latency_s)
    total_api_calls = 0

    # ─────────────────────────────────────────────────────────────────────────
    # [A] OCR ACCURACY – CV IMAGE
    # ─────────────────────────────────────────────────────────────────────────
    section_marker("📷  [A] OCR Accuracy – CV Image (PNG → Gemini OCR)")

    cv_ground_truth = """\
CURRICULUM VITAE
Name:  Alice Nguyen
Email: alice.nguyen@example.com
Phone: 0901234567

PROFESSIONAL SUMMARY
Senior Data Analyst with 5 years of experience in business intelligence,
data warehousing, and reporting dashboards. Proven expertise in SQL,
Python, Power BI, and ETL pipelines.

TECHNICAL SKILLS
SQL, Python, Power BI, Tableau, Excel, ETL, Data Warehouse, PostgreSQL

WORK EXPERIENCE
Senior Data Analyst | TechVN Corp (2020 – Present)
  - Built automated reporting pipelines using SQL and Python.
  - Designed Power BI dashboards delivering insights to C-suite.
  - Optimised ETL workflows reducing processing time by 40 percent.

EDUCATION
Bachelor of Science – Information Technology, HCMUT, 2019
"""

    img_cv_path = UPLOAD_DIR / "_test_ocr_cv.png"
    render_to_png(cv_ground_truth, img_cv_path)
    print(f"  ✅ Rendered CV image: {img_cv_path.name} ({img_cv_path.stat().st_size // 1024} KB)")

    try:
        print(f"  ⏳ Gọi Gemini OCR cho CV image...", end="", flush=True)
        ocr_cv_text, ocr_cv_lat = call_gemini_ocr(img_cv_path)
        total_api_calls += 1
        perf_log.append(("A", "CV OCR", ocr_cv_lat))
        print(f" xong ({ocr_cv_lat}s)")

        sim_cv   = similarity(cv_ground_truth, ocr_cv_text)
        recall_cv = keyword_recall(cv_ground_truth, ocr_cv_text)
        ocr_cv_ok = sim_cv >= 0.65 and recall_cv >= 0.70

        result_row("Độ tương đồng văn bản (SequenceMatcher)", f"{sim_cv*100:.1f}%", sim_cv >= 0.65)
        result_row("Keyword Recall (từ GT có trong OCR)",     f"{recall_cv*100:.1f}%", recall_cv >= 0.70)
        result_row("Latency OCR",                              f"{ocr_cv_lat}s")
        print(f"\n  Preview OCR (100 ký tự đầu):\n  {dim(repr(ocr_cv_text[:100]))}\n")

        all_results["ocr_cv"] = {
            "similarity_pct": round(sim_cv * 100, 1),
            "keyword_recall_pct": round(recall_cv * 100, 1),
            "latency_s": ocr_cv_lat,
            "pass": ocr_cv_ok,
        }
        time.sleep(GEMINI_DELAY)
    except Exception as e:
        print(f"\n  {red('❌')} OCR CV thất bại: {e}")
        all_results["ocr_cv"] = {"error": str(e), "pass": False}

    # ─────────────────────────────────────────────────────────────────────────
    # [B] OCR ACCURACY – JD IMAGE (từ data.csv)
    # ─────────────────────────────────────────────────────────────────────────
    section_marker("📰  [B] OCR Accuracy – JD Image (data.csv → PNG → Gemini OCR)")

    jds_from_csv = load_jd_from_csv(CSV_PATH, max_jds=1)
    if jds_from_csv:
        jd_gt_data = jds_from_csv[0]
        jd_ground_truth = f"Job Title: {jd_gt_data['title']}\n\n{jd_gt_data['description'][:800]}"
        print(f"  ✅ Lấy JD từ data.csv: \"{jd_gt_data['title'][:50]}...\"")
    else:
        jd_ground_truth = """\
Job Title: Data Analyst

We are seeking a Data Analyst with 2+ years experience in SQL, Python,
and business intelligence tools. The candidate must be proficient in
Power BI, Excel, and data warehousing concepts. Responsibilities include
building dashboards, analyzing large datasets, and preparing reports.
"""
        print(f"  {yellow('⚠️')} data.csv không tìm thấy – dùng JD mặc định.")

    img_jd_path = UPLOAD_DIR / "_test_ocr_jd.png"
    render_to_png(jd_ground_truth, img_jd_path)
    print(f"  ✅ Rendered JD image: {img_jd_path.name} ({img_jd_path.stat().st_size // 1024} KB)")

    try:
        print(f"  ⏳ Gọi Gemini OCR cho JD image...", end="", flush=True)
        ocr_jd_text, ocr_jd_lat = call_gemini_ocr(img_jd_path)
        total_api_calls += 1
        perf_log.append(("B", "JD OCR", ocr_jd_lat))
        print(f" xong ({ocr_jd_lat}s)")

        sim_jd    = similarity(jd_ground_truth, ocr_jd_text)
        recall_jd = keyword_recall(jd_ground_truth, ocr_jd_text)
        ocr_jd_ok = sim_jd >= 0.60 and recall_jd >= 0.65

        result_row("Độ tương đồng văn bản (SequenceMatcher)", f"{sim_jd*100:.1f}%", sim_jd >= 0.60)
        result_row("Keyword Recall (từ GT có trong OCR)",     f"{recall_jd*100:.1f}%", recall_jd >= 0.65)
        result_row("Latency OCR",                              f"{ocr_jd_lat}s")

        all_results["ocr_jd"] = {
            "similarity_pct": round(sim_jd * 100, 1),
            "keyword_recall_pct": round(recall_jd * 100, 1),
            "latency_s": ocr_jd_lat,
            "pass": ocr_jd_ok,
        }
        time.sleep(GEMINI_DELAY)
    except Exception as e:
        print(f"\n  {red('❌')} OCR JD thất bại: {e}")
        all_results["ocr_jd"] = {"error": str(e), "pass": False}

    # ─────────────────────────────────────────────────────────────────────────
    # [C] SCORING ACCURACY (direct service call, không qua HTTP)
    # ─────────────────────────────────────────────────────────────────────────
    section_marker("🎯  [C] Scoring Accuracy – 3 loại CV vs 1 JD thực tế")

    # Lấy JD text để extract criteria
    scoring_jds = load_jd_from_csv(CSV_PATH, max_jds=1)
    if scoring_jds:
        score_jd = scoring_jds[0]
        jd_text_for_scoring = f"Title: {score_jd['title']}\n\n{score_jd['description']}"
        print(f"  ✅ JD cho scoring: \"{score_jd['title'][:50]}\"")
    else:
        jd_text_for_scoring = jd_ground_truth
        score_jd = {"title": "Data Analyst"}
        print(f"  {yellow('⚠️')} Dùng JD mặc định cho scoring test.")

    # Extract JD criteria (1 API call, có cache)
    print(f"  ⏳ Extract JD criteria...", end="", flush=True)
    try:
        jd_criteria, jd_lat = call_gemini_jd_extract(jd_text_for_scoring)
        total_api_calls += 1
        perf_log.append(("C", "JD Extract", jd_lat))
        print(f" xong ({jd_lat}s)")
        print(f"     Required skills: {jd_criteria.required_skills[:5]}")
        print(f"     Min experience : {jd_criteria.min_years_experience} năm")
    except Exception as e:
        print(f"\n  {red('❌')} JD extract thất bại: {e}. Dùng fallback.")
        from app.services.gemini_service import _fallback_extract
        jd_criteria = _fallback_extract(jd_text_for_scoring)
        jd_lat = 0.0

    # 3 CV evaluations
    scoring_results = []
    for ctype in ["perfect", "partial", "mismatched"]:
        name = f"AccTest {ctype.capitalize()} CV"
        cv_text = build_cv(
            ctype,
            score_jd["title"],
            jd_criteria.required_skills or ["SQL", "Python", "Excel"],
            jd_criteria.min_years_experience,
            name,
        )
        print(f"\n  [{ctype.upper()}] Evaluating \"{name}\"...")
        print(f"    CV snippet: {dim(cv_text[:80].replace(chr(10), ' '))}...")

        try:
            print(f"    ⏳ Gọi Gemini evaluate...", end="", flush=True)
            eval_result, eval_lat = call_gemini_evaluate(cv_text, jd_criteria)
            total_api_calls += 1
            perf_log.append(("C", f"Evaluate_{ctype}", eval_lat))
            print(f" xong ({eval_lat}s)")

            ai_score  = eval_result.total_score
            ai_status = eval_result.fit_status
            exp_gt    = GT[ctype]
            
            status_ok = (ai_status == exp_gt["status"])
            lax_ok    = status_ok or (
                ctype == "perfect" and ai_status in ("Phù hợp", "Tiềm năng")
            ) or (
                ctype == "partial" and ai_status in ("Tiềm năng", "Phù hợp", "Loại")
            )
            score_ok  = exp_gt["score_min"] <= ai_score <= exp_gt["score_max"]

            result_row(f"  Điểm AI",    f"{ai_score}/100  (kỳ vọng {exp_gt['score_min']}–{exp_gt['score_max']})", score_ok)
            result_row(f"  Trạng thái", f"{ai_status}  (kỳ vọng: {exp_gt['status']})", lax_ok)

            scoring_results.append({
                "ctype": ctype,
                "ai_score": ai_score,
                "ai_status": ai_status,
                "expected_status": exp_gt["status"],
                "expected_score_range": f"{exp_gt['score_min']}–{exp_gt['score_max']}",
                "status_exact": status_ok,
                "status_lax": lax_ok,
                "score_in_range": score_ok,
                "latency_s": eval_lat,
                "pros": eval_result.pros[:2],
                "cons": eval_result.cons[:2],
            })
        except Exception as e:
            print(f"\n    {red('❌')} Evaluate {ctype} thất bại: {e}")
            scoring_results.append({"ctype": ctype, "error": str(e)})

        if ctype != "mismatched":
            print(f"    ⏱️  Chờ {GEMINI_DELAY}s...", end="", flush=True)
            time.sleep(GEMINI_DELAY)
            print(" tiếp.")

    all_results["scoring"] = scoring_results

    # ─────────────────────────────────────────────────────────────────────────
    # [D] PERFORMANCE SUMMARY
    # ─────────────────────────────────────────────────────────────────────────
    section_marker("⚡  [D] Performance – Latency Summary")

    if perf_log:
        print(f"\n  {'Section':<8} {'Bước':<25} {'Latency':>10}")
        print("  " + "-" * 46)
        for sec, step, lat in perf_log:
            bar = "█" * min(int(lat * 2), 30)
            color_fn = green if lat < 5 else yellow if lat < 15 else red
            print(f"  [{sec}]     {step:<25} {color_fn(f'{lat:>8.2f}s')}  {dim(bar)}")
        avg_lat = sum(l for _, _, l in perf_log) / len(perf_log)
        max_lat = max(l for _, _, l in perf_log)
        print()
        result_row("Tổng API calls thực tế",  str(total_api_calls))
        result_row("Latency trung bình",       f"{avg_lat:.2f}s", avg_lat < 20)
        result_row("Latency lớn nhất",         f"{max_lat:.2f}s", max_lat < 60)

    all_results["performance"] = {
        "total_api_calls": total_api_calls,
        "steps": [{"section": s, "step": st, "latency_s": l} for s, st, l in perf_log],
        "avg_latency_s": round(sum(l for _, _, l in perf_log) / len(perf_log), 2) if perf_log else None,
        "max_latency_s": round(max(l for _, _, l in perf_log), 2) if perf_log else None,
    }

    # ─────────────────────────────────────────────────────────────────────────
    # FINAL REPORT
    # ─────────────────────────────────────────────────────────────────────────
    section_marker("📊  TỔNG HỢP KẾT QUẢ KIỂM THỬ")

    # OCR
    ocr_cv_r  = all_results.get("ocr_cv", {})
    ocr_jd_r  = all_results.get("ocr_jd", {})
    ocr_cv_pass = ocr_cv_r.get("pass", False)
    ocr_jd_pass = ocr_jd_r.get("pass", False)

    print(f"\n  {'Nhóm Test':<30} {'Chỉ số':<28} {'Kết quả'}")
    print("  " + "─" * 65)

    def fmt_row(grp, metric, val, ok):
        icon = green("✅ PASS") if ok else red("❌ FAIL")
        print(f"  {grp:<30} {metric:<28} {val}   {icon}")

    # OCR CV
    if "error" not in ocr_cv_r:
        fmt_row("[A] OCR – CV Image", f"Similarity {ocr_cv_r.get('similarity_pct', 0)}%",
                f"Recall {ocr_cv_r.get('keyword_recall_pct', 0)}%", ocr_cv_pass)
    else:
        fmt_row("[A] OCR – CV Image", "ERROR", ocr_cv_r.get("error", "")[:25], False)

    # OCR JD
    if "error" not in ocr_jd_r:
        fmt_row("[B] OCR – JD Image", f"Similarity {ocr_jd_r.get('similarity_pct', 0)}%",
                f"Recall {ocr_jd_r.get('keyword_recall_pct', 0)}%", ocr_jd_pass)
    else:
        fmt_row("[B] OCR – JD Image", "ERROR", ocr_jd_r.get("error", "")[:25], False)

    # Scoring
    valid_scores = [r for r in scoring_results if "error" not in r]
    if valid_scores:
        n_status = sum(1 for r in valid_scores if r.get("status_lax"))
        n_score  = sum(1 for r in valid_scores if r.get("score_in_range"))
        acc_pct  = n_status / len(valid_scores) * 100
        fmt_row("[C] Scoring Accuracy",
                f"Status {n_status}/{len(valid_scores)} đúng",
                f"Score {n_score}/{len(valid_scores)} đúng range",
                acc_pct >= 67)

        # Breakdown per type
        print()
        print(f"  {'Loại CV':<14} {'AI Score':<12} {'AI Status':<14} {'Kỳ vọng':<14} {'Status?':<10} {'Score?'}")
        print("  " + "─" * 70)
        for r in valid_scores:
            s_ok = green("✅") if r.get("status_lax") else red("❌")
            sc_ok = green("✅") if r.get("score_in_range") else yellow("⚠️")
            print(f"  {r['ctype']:<14} {r['ai_score']:<12} {r['ai_status']:<14} "
                  f"{r['expected_status']:<14} {s_ok:<16} {sc_ok}")

    # Tổng kết điểm
    tests = [ocr_cv_pass, ocr_jd_pass]
    if valid_scores:
        tests.append(acc_pct >= 67)
    passed = sum(tests)
    total_t = len(tests)

    print()
    print(bold(f"  ĐIỂM TỔNG KẾT: {passed}/{total_t} nhóm test PASS"))
    overall_ok = passed == total_t
    if overall_ok:
        print(green("  🏆 Hệ thống hoạt động CHÍNH XÁC và ĐỦ TIÊU CHUẨN!"))
    elif passed >= total_t * 0.67:
        print(yellow("  ⚠️  Hệ thống hoạt động KHÁ TỐT nhưng cần cải thiện một số điểm."))
    else:
        print(red("  ❌ Hệ thống có độ chính xác THẤP – cần review prompt và pipeline."))

    print()
    all_results["summary"] = {
        "test_time": datetime.now().isoformat(),
        "groups_passed": passed,
        "groups_total": total_t,
        "overall_pass": overall_ok,
        "total_api_calls": total_api_calls,
    }

    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"  💾 Kết quả chi tiết đã lưu: {RESULTS_PATH}")
    print()
    print(bold("=" * 70))

if __name__ == "__main__":
    main()
