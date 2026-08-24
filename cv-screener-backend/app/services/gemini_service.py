import json
import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

logger = logging.getLogger(__name__)

from app.schemas import CVEvaluationSchema, JDCriteriaSchema

TECH_KEYWORDS = [
    "python", "fastapi", "sqlalchemy", "docker", "kubernetes", "aws", "azure", "gcp", "postgresql",
    "mysql", "redis", "mongodb", "sqlite", "oracle", "snowflake", "bigquery", "redshift", "hadoop",
    "spark", "pyspark", "databricks", "etl", "elt", "airflow", "kafka", "dax", "vba", "alteryx", "looker",
    "qlik", "tableau", "power bi", "powerbi", "excel", "javascript", "typescript", "react", "node",
    "java", "c#", "go", "linux", "graphql", "api", "backend", "database", "csdl", "hệ thống", "system",
    "deployment", "devops", "git", "jira", "ssis", "ssrs", "ssas", "sql server"
]

SKILL_ALIASES = {
    # Programming & Frameworks
    "python": ["python", "py", "django", "flask", "fastapi", "numpy", "pandas", "scipy", "statsmodels", "pyspark"],
    "fastapi": ["fastapi", "api rest", "rest api", "fast api"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "reactjs", "react.js"],
    "node": ["node", "nodejs", "node.js"],
    "java": ["java", "spring", "springboot", "spring boot"],
    "c#": ["c#", "csharp", "net", "dot net", "dotnet"],
    "go": ["go", "golang"],
    "graphql": ["graphql", "gql"],
    "api": ["api", "rest api", "restful api", "backend api", "web service", "graphql", "microservices"],
    "backend": ["backend", "back-end", "server-side", "server side"],

    # Databases & SQL
    "sql": ["sql", "t-sql", "tsql", "pl/sql", "plsql", "sqlite"],
    "postgresql": ["postgresql", "postgres", "sql", "psql"],
    "mysql": ["mysql", "sql", "my sql"],
    "oracle": ["oracle", "oracle database", "pl/sql"],
    "sql server": ["sql server", "mssql", "microsoft sql server", "ssis", "ssrs", "ssas"],
    "snowflake": ["snowflake"],
    "bigquery": ["bigquery", "google bigquery"],
    "redshift": ["redshift", "amazon redshift"],
    "mongodb": ["mongodb", "mongo"],
    "nosql": ["nosql", "non-relational database", "document store"],
    "redis": ["redis", "in-memory database"],
    "database": ["database", "cơ sở dữ liệu", "csdl", "qlcsdl", "sql", "nosql", "datastore", "rdbms", "database management"],

    # BI, Visualization & Analytics Tools
    "power bi": ["power bi", "powerbi", "pbi", "dax", "power query", "power pivot"],
    "tableau": ["tableau", "tableau desktop", "tableau server", "tableau prep"],
    "excel": ["excel", "microsoft excel", "vba", "pivot tables", "vlookup", "index match", "advanced excel"],
    "looker": ["looker", "lookml"],
    "alteryx": ["alteryx"],
    "qlik": ["qlik", "qlikview", "qliksense"],
    "sas": ["sas", "sas enterprise"],
    "spss": ["spss", "pasw"],
    "stata": ["stata"],

    # Data Engineering & Infrastructure
    "etl": ["etl", "elt", "data extraction", "data transformation", "data loading", "ssis", "data pipeline", "data pipelines", "pipeline development"],
    "data warehousing": ["data warehouse", "data warehousing", "edw", "enterprise data warehouse", "star schema", "snowflake schema", "data mart"],
    "data governance": ["data governance", "data stewardship", "data lineage", "data dictionary", "data quality", "data catalog"],
    "data modeling": ["data modeling", "data model", "dimensional modeling", "er diagram", "er-diagram"],
    "data architecture": ["data architecture", "data architect"],
    "azure": ["azure", "azure data factory", "adf", "azure synapse", "azure databricks"],
    "aws": ["aws", "amazon web services", "cloud", "redshift", "s3", "glue", "athena", "lambda"],
    "gcp": ["gcp", "google cloud", "google cloud platform", "bigquery"],
    "hadoop": ["hadoop", "hdfs", "hive", "pig"],
    "spark": ["spark", "pyspark", "apache spark"],
    "databricks": ["databricks"],
    "airflow": ["airflow", "apache airflow"],
    "kafka": ["kafka", "apache kafka"],
    "docker": ["docker", "container", "containers", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "linux": ["linux", "ubuntu", "unix", "centos", "redhat", "shell", "bash"],
    "system deployment": ["triển khai hệ thống", "deploy hệ thống", "deployment", "devops", "system deployment", "ci/cd"],

    # Data Science, AI & Machine Learning
    "data science": ["data science", "data scientist"],
    "machine learning": ["machine learning", "ml", "supervised learning", "unsupervised learning", "scikit-learn", "sklearn"],
    "deep learning": ["deep learning", "dl", "tensorflow", "pytorch", "keras", "neural networks"],
    "ai": ["ai", "artificial intelligence", "genai", "generative ai", "llm", "trí tuệ nhân tạo"],
    "nlp": ["nlp", "natural language processing", "text mining"],
    "predictive modeling": ["predictive modeling", "predictive analytics", "predictive model", "forecasting model"],
    "statistical analysis": ["statistical analysis", "statistics", "statistical modeling", "hypothesis testing", "regression", "anova"],
    "forecasting": ["forecasting", "time series", "time-series", "predictive forecasting"],
    "a/b testing": ["a/b testing", "ab testing", "split testing", "hypothesis testing"],
    "segmentation": ["segmentation", "customer segmentation", "clustering"],
    "data mining": ["data mining"],
    "business intelligence": ["business intelligence", "bi", "bi reporting", "bi dashboard"],
    "visualization": ["visualization", "data visualization", "visualizations", "reporting dashboards"],

    # Enterprise Software & Tools
    "salesforce": ["salesforce", "sfdc", "salesforce crm"],
    "sap": ["sap", "sap bw", "sap hana", "sap erp"],
    "workday": ["workday"],
    "hubspot": ["hubspot"],
    "epic": ["epic", "epic systems", "ehr", "emr"],
    "cerner": ["cerner"],
    "gis": ["gis", "arcgis", "qgis", "geographic information system"],
    "jira": ["jira", "confluence", "atlassian"],
    "git": ["git", "github", "gitlab", "bitbucket"],

    # Business, Management & Industry Domains
    "sales": ["sales", "bán hàng", "kinh doanh", "telesales", "account executive", "account manager", "chăm sóc khách hàng"],
    "marketing": ["marketing", "seo", "sem", "content creator", "digital marketing", "social media", "pr", "ads", "market research", "marketing analytics"],
    "business analyst": ["business analyst", "ba", "analyst", "phân tích nghiệp vụ", "business analysis"],
    "project management": ["project manager", "pm", "quản lý dự án", "project management", "scrum", "agile", "pmp"],
    "hr": ["hr", "human resources", "nhân sự", "recruitment", "tuyển dụng", "people analytics"],
    "accounting": ["accounting", "kế toán", "finance", "tài chính", "financial analysis", "auditing", "kiểm toán"],
    "customer service": ["customer service", "chăm sóc khách hàng", "cskh", "customer success", "customer support"],
    "crm": ["crm", "customer relationship management", "salesforce", "hubspot"],
    "erp": ["erp", "enterprise resource planning", "sap", "oracle erp"]
}

IT_KEYWORDS = [
    "developer", "engineer", "programmer", "lập trình viên", "coder", "software", "phần mềm",
    "backend", "frontend", "fullstack", "devops", "system", "hệ thống", "database", "cơ sở dữ liệu",
    "csdl", "cloud", "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "ci/cd", "git",
    "python", "javascript", "typescript", "java", "c#", "csharp", "c++", "golang", "php", "ruby", "rust",
    "react", "vue", "angular", "nextjs", "node", "nodejs", "fastapi", "django", "spring", "laravel",
    "postgresql", "mysql", "mongodb", "redis", "oracle", "sql", "nosql", "qa", "qc", "tester", "kiem thu",
    "data science", "machine learning", "ai", "artificial intelligence", "trí tuệ nhân tạo",
    "power bi", "powerbi", "tableau", "snowflake", "bigquery", "redshift", "etl", "elt", "data warehousing",
    "data governance", "data modeling", "data architecture", "data pipeline", "pyspark", "spark", "hadoop",
    "databricks", "airflow", "kafka", "looker", "alteryx", "qlik", "sas", "spss", "stata"
]

BUSINESS_KEYWORDS = [
    "sales", "bán hàng", "kinh doanh", "telesales", "account executive", "account manager",
    "marketing", "seo", "sem", "content", "pr", "event", "branding", "digital marketing", "market research",
    "business analyst", "ba", "product owner", "po", "project manager", "pm", "quản lý dự án", "scrum", "agile",
    "customer service", "chăm sóc khách hàng", "cskh", "customer success", "customer support",
    "finance", "tài chính", "financial analysis", "accounting", "kế toán", "auditing", "kiem toan",
    "hr", "human resources", "nhân sự", "recruitment", "tuyển dụng", "people analytics",
    "administration", "hành chính", "operations", "vận hành", "crm", "erp", "consultant", "tư vấn",
    "business intelligence", "bi", "reporting", "dashboard", "dashboards", "visualization", "metrics", "kpi", "kpis",
    "salesforce", "sap", "workday", "hubspot", "epic", "cerner"
]

import sqlite3
import hashlib

def get_cached_response(cache_key_source: str) -> str | None:
    """Retrieve a cached response from sqlite database to speed up and save costs."""
    try:
        conn = sqlite3.connect("cv_screener.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS gemini_cache (key TEXT PRIMARY KEY, response TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        key_hash = hashlib.sha256(cache_key_source.encode("utf-8")).hexdigest()
        cursor.execute("SELECT response FROM gemini_cache WHERE key = ?", (key_hash,))
        row = cursor.fetchone()
        conn.close()
        if row:
            logger.info("Cache hit for Gemini request")
            return row[0]
    except Exception as e:
        logger.error(f"Error reading cache: {e}")
    return None

def set_cached_response(cache_key_source: str, response: str) -> None:
    """Save a response into sqlite database cache."""
    try:
        conn = sqlite3.connect("cv_screener.db")
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS gemini_cache (key TEXT PRIMARY KEY, response TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        key_hash = hashlib.sha256(cache_key_source.encode("utf-8")).hexdigest()
        cursor.execute("INSERT OR REPLACE INTO gemini_cache (key, response) VALUES (?, ?)", (key_hash, response))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error writing cache: {e}")

def detect_industry(text: str) -> str:
    """Classify the industry/class of the JD or CV based on keywords."""
    normalized = _normalize_text(text)
    it_score = sum(1 for keyword in IT_KEYWORDS if keyword in normalized)
    biz_score = sum(1 for keyword in BUSINESS_KEYWORDS if keyword in normalized)
    if it_score > biz_score and it_score > 0:
        return "IT"
    elif biz_score > it_score and biz_score > 0:
        return "BUSINESS"
    return "GENERAL"

def pre_match_cv_with_jd(cv_text: str, jd_criteria: dict) -> dict:
    """Match terms before evaluating with AI to optimize accuracy and speed."""
    print(f"[MATCHING WORD] Bắt đầu khớp từ khóa CV vs JD. CV length={len(cv_text)}, JD required_skills={jd_criteria.get('required_skills', [])}")
    logger.info(f"[MATCHING WORD] Bắt đầu khớp từ khóa. Required skills: {jd_criteria.get('required_skills', [])}")
    normalized_cv = _normalize_text(cv_text)
    
    required_skills = jd_criteria.get("required_skills") or []
    if isinstance(required_skills, str):
        required_skills = [required_skills]
    
    preferred_skills = jd_criteria.get("preferred_skills") or []
    if isinstance(preferred_skills, str):
        preferred_skills = [preferred_skills]
        
    matched_required = []
    missing_required = []
    for skill in required_skills:
        if _match_skill_in_text(normalized_cv, skill):
            matched_required.append(skill)
        else:
            missing_required.append(skill)
            
    matched_preferred = []
    for skill in preferred_skills:
        if _match_skill_in_text(normalized_cv, skill):
            matched_preferred.append(skill)

    # Detect experience years in CV
    # Look for patterns of years of experience
    exp_matches = re.findall(r"(\d+)\s*(?:năm|year|yr)s?\s*(?:kinh\s*nghiệm|experience|work|làm\s*việc)", normalized_cv)
    detected_years = 0
    if exp_matches:
        detected_years = max(int(y) for y in exp_matches)
    else:
        # Fallback to simple number + year match
        simple_matches = re.findall(r"(?:từ|có|kinh\s*nghiệm|experience)\s*(\d+)\s*(?:năm|year)", normalized_cv)
        if simple_matches:
            detected_years = max(int(y) for y in simple_matches)
            
    # Education matching status
    education_req = jd_criteria.get("education_requirement") or ""
    edu_match_status = "Không có yêu cầu đặc biệt"
    if education_req:
        edu_req_norm = _normalize_text(education_req)
        if any(term in edu_req_norm for term in ["đại học", "university", "cử nhân", "bachelor", "kỹ sư", "engineer"]):
            if any(term in normalized_cv for term in ["đại học", "university", "cử nhân", "bachelor", "kỹ sư", "engineer"]):
                edu_match_status = "Đạt yêu cầu (Đại học/Cử nhân)"
            else:
                edu_match_status = "Chưa rõ (Không thấy bằng Đại học/Cử nhân)"
        elif any(term in edu_req_norm for term in ["cao đẳng", "college"]):
            if any(term in normalized_cv for term in ["cao đẳng", "college", "đại học", "university"]):
                edu_match_status = "Đạt yêu cầu (Cao đẳng trở lên)"
            else:
                edu_match_status = "Chưa rõ (Không thấy bằng Cao đẳng/Đại học)"
        elif any(term in edu_req_norm for term in ["thạc sĩ", "master", "mba"]):
            if any(term in normalized_cv for term in ["thạc sĩ", "master", "mba"]):
                edu_match_status = "Đạt yêu cầu (Thạc sĩ/MBA)"
            else:
                edu_match_status = "Chưa rõ (Không thấy bằng Thạc sĩ)"

    industry = detect_industry(cv_text + " " + json.dumps(jd_criteria))

    result = {
        "industry": industry,
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "detected_years_experience": detected_years,
        "education_match_status": edu_match_status
    }
    print(f"[MATCHING WORD] Kết quả khớp từ khóa: Ngành={industry} | Kỹ năng khớp={matched_required} | Kỹ năng thiếu={missing_required} | Năm KN={detected_years} | Học vấn={edu_match_status}")
    logger.info(f"[MATCHING WORD] Kết quả: matched={matched_required}, missing={missing_required}, years={detected_years}, industry={industry}")
    return result


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.lower()).strip()


def _match_skill_in_text(text: str, skill_name: str) -> bool:
    normalized = _normalize_text(text)
    skill_lower = skill_name.lower().strip()
    aliases = SKILL_ALIASES.get(skill_lower, [skill_lower])
    
    for alias in aliases:
        if len(alias) <= 3 or alias in {"c#", "c++", "go", "js", "ts", "py", "ba", "pm", "hr"}:
            escaped = re.escape(alias)
            if alias.endswith("#") or alias.endswith("+"):
                pattern = r"\b" + escaped
            else:
                pattern = r"\b" + escaped + r"\b"
            if re.search(pattern, normalized):
                return True
        else:
            if alias in normalized:
                return True
    return False


def _get_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def _get_client() -> genai.Client:
    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY hoặc GOOGLE_API_KEY chưa được cấu hình.")
    return genai.Client(api_key=api_key)


def _fallback_extract(raw_text: str) -> JDCriteriaSchema:
    text = _normalize_text(raw_text)
    required_skills = []
    for skill_name in SKILL_ALIASES:
        if _match_skill_in_text(text, skill_name):
            required_skills.append(skill_name)

    if not required_skills:
        required_skills = [keyword for keyword in TECH_KEYWORDS if keyword in text]

    text_without_no_requirement = text.replace("không yêu cầu kinh nghiệm", "")
    years_match = re.search(r"(?:tối\s*thiểu|ít\s*nhất|từ|là)\s*(\d+)\s*năm\s*(?:kinh\s*nghiệm|experience)|(?:experience|kinh\s*nghiệm)\s*(?:từ\s*)?(\d+)", text_without_no_requirement)
    min_years_experience = int(years_match.group(1) or years_match.group(2) or 0) if years_match else 0
    if "không yêu cầu kinh nghiệm" in text or "không bắt buộc kinh nghiệm" in text or "no experience required" in text:
        min_years_experience = 0

    education_requirement = None
    if "đại học" in text or "university" in text:
        education_requirement = "Đại học"
    elif "cao đẳng" in text or "college" in text:
        education_requirement = "Cao đẳng"
    elif "thạc sĩ" in text or "master" in text:
        education_requirement = "Thạc sĩ"

    responsibilities = []
    for sentence in re.split(r"[.;\n]+", raw_text):
        clean_sentence = sentence.strip()
        lowered = clean_sentence.lower()
        if 3 <= len(clean_sentence) <= 180 and any(word in lowered for word in [
            "chịu trách nhiệm",
            "phát triển",
            "thiết kế",
            "quản lý",
            "xây dựng",
            "hỗ trợ",
            "thực hiện",
            "triển khai",
            "quản trị",
            "đảm nhiệm",
            "build",
            "develop",
            "design",
            "implement",
        ]):
            responsibilities.append(clean_sentence)

    return JDCriteriaSchema(
        required_skills=list(dict.fromkeys(required_skills))[:10],
        preferred_skills=[],
        min_years_experience=min_years_experience,
        education_requirement=education_requirement,
        key_responsibilities=responsibilities[:5],
    )


def enrich_sparse_jd_criteria(raw_text: str, current_criteria: JDCriteriaSchema) -> JDCriteriaSchema:
    api_key = _get_api_key()
    if not api_key:
        return current_criteria
    
    prompt = f"""
    Bạn là một chuyên gia tuyển dụng cao cấp.
    Hồ sơ mô tả công việc (JD) sau khi chạy OCR trả về văn bản quá ngắn, thiếu thông tin hoặc bị lỗi nhận dạng chữ.
    
    Văn bản thô nhận dạng được:
    \"\"\"
    {raw_text}
    \"\"\"
    
    Kết quả trích xuất hiện tại (rất thiếu thông tin):
    {current_criteria.model_dump_json()}
    
    Yêu cầu:
    Dựa vào các từ khóa ít ỏi trong văn bản thô, hãy tái cấu trúc và làm giàu thêm thông tin cho các thuộc tính sau một cách hợp lý và thực tế nhất:
    - required_skills (bắt buộc đề xuất các kỹ năng/công nghệ phổ biến cho vị trí này, tối thiểu 3 kỹ năng)
    - preferred_skills (bổ sung các kỹ năng ưu tiên phù hợp)
    - min_years_experience (ước lượng số năm kinh nghiệm tối thiểu hợp lý)
    - education_requirement (bổ sung yêu cầu bằng cấp phổ biến)
    - key_responsibilities (bổ sung trách nhiệm chính, tối thiểu 3 nhiệm vụ)
    
    Chỉ trả về JSON phù hợp.
    """
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )
        data = json.loads(response.text)
        payload = data.get("candidate_evaluation") if isinstance(data, dict) and "candidate_evaluation" in data else data
        enriched = JDCriteriaSchema(**payload)
        return enriched
    except Exception as e:
        logger.error(f"Gemini enrichment failed: {e}")
        return current_criteria


def extract_jd_criteria(raw_text: str) -> JDCriteriaSchema:
    if not raw_text or not raw_text.strip():
        raise ValueError("raw_text không được để trống.")

    print(f"[JD READER] Bắt đầu đọc/trích xuất JD. Text length={len(raw_text)}. Preview: {raw_text[:150].strip()!r}")
    logger.info(f"[JD READER] Đang trích xuất tiêu chí từ JD. Text length={len(raw_text)}")

    # Cache Lookup
    cache_key = f"jd_criteria_{raw_text}"
    cached = get_cached_response(cache_key)
    if cached:
        try:
            result = JDCriteriaSchema(**json.loads(cached))
            # Check if sparse and enrich if needed
            sparse_count = 0
            if len(result.required_skills) < 1: sparse_count += 1
            if len(result.key_responsibilities) < 1: sparse_count += 1
            if len(result.preferred_skills) < 1: sparse_count += 1
            if result.min_years_experience < 1: sparse_count += 1
            if sparse_count >= 2:
                print("[WARNING] JD criteria from OCR is too sparse. Triggering special Gemini API recovery/fallback mechanism to enrich the description...")
                result = enrich_sparse_jd_criteria(raw_text, result)
                print("[INFO] Special Gemini API recovery completed.")
            return result
        except Exception:
            pass

    api_key = _get_api_key()
    if not api_key:
        result = _fallback_extract(raw_text)
    else:
        prompt = f"""
        Bạn là một chuyên gia Tuyển dụng nhân sự (Tech/Business HR).
        Hãy phân tích đoạn văn bản mô tả công việc (Job Description) dưới đây và trích xuất thông tin tiêu chí tuyển dụng một cách chính xác nhất.

        Nội dung Job Description:
        \"\"\"
        {raw_text}
        \"\"\"
        """
        try:
            client = _get_client()
            response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            data = json.loads(response.text)
            payload = data.get("candidate_evaluation") if isinstance(data, dict) and "candidate_evaluation" in data else data
            result = JDCriteriaSchema(**payload)
            set_cached_response(cache_key, response.text)
        except Exception as exc:
            logger.exception("Gemini JD extraction failed")
            result = _fallback_extract(raw_text)

    # Check if sparse
    sparse_count = 0
    if len(result.required_skills) < 1: sparse_count += 1
    if len(result.key_responsibilities) < 1: sparse_count += 1
    if len(result.preferred_skills) < 1: sparse_count += 1
    if result.min_years_experience < 1: sparse_count += 1
    
    if sparse_count >= 2:
        print("[JD READER][WARNING] JD criteria quá ít thông tin. Đang kích hoạt Gemini API để bổ sung...")
        result = enrich_sparse_jd_criteria(raw_text, result)
        print("[JD READER][INFO] Gemini API bổ sung JD criteria hoàn tất.")

    print(f"[JD READER] Đọc JD xong. required_skills={result.required_skills} | min_years={result.min_years_experience} | education={result.education_requirement}")
    logger.info(f"[JD READER] Trích xuất JD hoàn tất. Skills={result.required_skills}, min_years={result.min_years_experience}")
    return result


def extract_jd_criteria_from_image(image_path: str) -> JDCriteriaSchema:
    image_file = Path(image_path)
    if not image_file.exists() or not image_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy file ảnh JD tại: {image_path}")

    suffix = image_file.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("Chỉ hỗ trợ file ảnh JPG, JPEG hoặc PNG cho JD image ingest.")

    # Cache check based on file hash or file path
    try:
        file_hash = hashlib.sha256(image_file.read_bytes()).hexdigest()
        cache_key = f"jd_criteria_image_{file_hash}"
        cached = get_cached_response(cache_key)
        if cached:
            return JDCriteriaSchema(**json.loads(cached))
    except Exception:
        cache_key = None

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY hoặc GOOGLE_API_KEY chưa được cấu hình để đọc ảnh JD bằng Gemini.")

    mime_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    image_bytes = image_file.read_bytes()

    prompt = """
    Bạn là chuyên gia tuyển dụng. Hãy đọc hình ảnh chứa Job Description và trích xuất thông tin sau:
    - required_skills
    - preferred_skills
    - min_years_experience
    - education_requirement
    - key_responsibilities

    Chỉ trả về JSON hợp lệ theo schema được quy định. Nếu không thấy thông tin, trả về giá trị mặc định phù hợp.
    """

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )
        data = json.loads(response.text)
        payload = data.get("candidate_evaluation") if isinstance(data, dict) and "candidate_evaluation" in data else data
        result = JDCriteriaSchema(**payload)
        
        if cache_key:
            set_cached_response(cache_key, response.text)
        return result
    except Exception as exc:
        logger.exception("Gemini image JD extraction failed")
        raise RuntimeError(f"Lỗi khi trích xuất JD từ ảnh: {exc}") from exc


def extract_text_from_image(image_path: str) -> str:
    image_file = Path(image_path)
    if not image_file.exists() or not image_file.is_file():
        raise FileNotFoundError(f"Không tìm thấy file ảnh tại: {image_path}")

    suffix = image_file.suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png"}:
        raise ValueError("Chỉ hỗ trợ file ảnh JPG, JPEG hoặc PNG để trích xuất text bằng Gemini.")

    try:
        file_hash = hashlib.sha256(image_file.read_bytes()).hexdigest()
        cache_key = f"image_ocr_{file_hash}"
        cached = get_cached_response(cache_key)
        if cached:
            return cached
    except Exception:
        cache_key = None

    api_key = _get_api_key()
    if not api_key:
        raise ValueError("GEMINI_API_KEY hoặc GOOGLE_API_KEY chưa được cấu hình để đọc ảnh bằng Gemini.")

    image_bytes = image_file.read_bytes()
    mime_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
    prompt = """
    Hãy đọc hình ảnh này và trả về toàn bộ văn bản có trong ảnh, giữ nguyên nội dung theo kiểu plain text.
    Nếu hình ảnh là CV hoặc Job Description, hãy giữ nguyên tên, kỹ năng, kinh nghiệm, học vấn và trách nhiệm công việc.
    Trả về văn bản sạch, không thêm giải thích.
    """

    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
            config=types.GenerateContentConfig(
                response_mime_type="text/plain",
                temperature=0.1,
            ),
        )
        res_text = response.text.strip() if getattr(response, "text", None) else ""
        if cache_key and res_text:
            set_cached_response(cache_key, res_text)
        return res_text
    except Exception as exc:
        logger.exception("Gemini OCR failed")
        raise RuntimeError(f"Lỗi khi OCR ảnh bằng Gemini: {exc}") from exc


def _normalize_skill_match(value):
    if value is None:
        return []
    if isinstance(value, dict):
        items = []
        for skill, detail in value.items():
            if isinstance(detail, dict):
                description = detail.get("detail") or detail.get("description") or detail.get("summary") or json.dumps(detail, ensure_ascii=False)
            elif isinstance(detail, list):
                description = ", ".join(str(item) for item in detail)
            else:
                description = str(detail)
            items.append({"skill": str(skill), "detail": description})
        return items
    if isinstance(value, list):
        items = []
        for item in value:
            if isinstance(item, dict):
                skill = item.get("skill") or item.get("name") or item.get("technology") or "Unknown"
                detail = item.get("detail") or item.get("description") or item.get("summary") or item.get("match") or ""
                items.append({"skill": str(skill), "detail": str(detail)})
            elif isinstance(item, str):
                items.append({"skill": item, "detail": "Đã đề cập trong CV"})
        return items
    if isinstance(value, str):
        return [{"skill": "General", "detail": value}]
    return []


def _normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        result = []
        for item in value:
            if isinstance(item, dict):
                result.append(item.get("text") or item.get("detail") or item.get("summary") or str(item))
            else:
                result.append(str(item))
        return result
    return [str(value)]


def _normalize_evaluation_payload(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return {}

    normalized = dict(payload)

    if "total_score" not in normalized and "score" in normalized:
        normalized["total_score"] = normalized["score"]
    if "skills_match" not in normalized and "skills" in normalized:
        normalized["skills_match"] = normalized["skills"]
    if "experience_match" not in normalized and "experience" in normalized:
        normalized["experience_match"] = normalized["experience"]
    if "pros" not in normalized and "strengths" in normalized:
        normalized["pros"] = normalized["strengths"]
    if "cons" not in normalized and "weaknesses" in normalized:
        normalized["cons"] = normalized["weaknesses"]
    if "fit_status" not in normalized and "recommendation" in normalized:
        normalized["fit_status"] = normalized["recommendation"]

    normalized["skills_match"] = _normalize_skill_match(normalized.get("skills_match"))
    normalized["experience_match"] = str(normalized.get("experience_match") or normalized.get("experience") or "Không có đánh giá rõ ràng.")
    normalized["pros"] = _normalize_string_list(normalized.get("pros") or [])
    normalized["cons"] = _normalize_string_list(normalized.get("cons") or [])
    normalized["fit_status"] = str(normalized.get("fit_status") or normalized.get("recommendation") or normalized.get("status") or "Tiềm năng")
    normalized["total_score"] = int(normalized.get("total_score", 0) or 0)

    return normalized


def _score_cv_locally(cv_text: str, jd_criteria: dict, pre_match: dict = None) -> CVEvaluationSchema:
    if pre_match is None:
        pre_match = pre_match_cv_with_jd(cv_text, jd_criteria)
        
    required_skills = jd_criteria.get("required_skills") or []
    if isinstance(required_skills, str):
        required_skills = [required_skills]
        
    matched_skills = pre_match["matched_required_skills"]
    missing_skills = pre_match["missing_required_skills"]
    
    experience_requirement = int(jd_criteria.get("min_years_experience", 0) or 0)
    actual_years = pre_match["detected_years_experience"]
    
    score = 0
    if required_skills:
        score += min(50, (len(matched_skills) / max(len(required_skills), 1)) * 50)
    else:
        score += 30
        
    if experience_requirement > 0:
        ratio = min(1.0, actual_years / experience_requirement)
        score += ratio * 20
        if actual_years >= experience_requirement:
            score += 5
    else:
        if actual_years > 0:
            score += 20
        else:
            score += 15
            
    normalized_text = _normalize_text(cv_text)
    if pre_match["industry"] == "IT":
        keywords = ["phát triển", "triển khai", "thiết kế", "xây dựng", "hệ thống", "api", "database"]
    else:
        keywords = ["bán hàng", "kinh doanh", "marketing", "quản lý", "tư vấn", "chăm sóc khách hàng"]
        
    if any(k in normalized_text for k in keywords):
        score += 15
        
    if "Đạt yêu cầu" in pre_match["education_match_status"] or not jd_criteria.get("education_requirement"):
        score += 10
    else:
        score += 5
        
    total_score = max(0, min(100, int(round(score))))
    fit_status = "Phù hợp" if total_score >= 75 else "Tiềm năng" if total_score >= 55 else "Loại"
    
    skills_match = [
        {"skill": skill, "detail": "Phù hợp (Đã khớp từ khóa)." if skill in matched_skills else "Thiếu hoặc chưa rõ trong CV."}
        for skill in required_skills
    ]
    if not skills_match:
        skills_match = [{"skill": "General", "detail": "Chưa có dữ liệu kỹ năng rõ ràng trong JD/CV."}]
        
    pros = []
    if matched_skills:
        pros.append(f"Có kỹ năng quan trọng phù hợp: {', '.join(matched_skills[:5])}.")
    if actual_years >= experience_requirement and experience_requirement > 0:
        pros.append(f"Đáp ứng đủ số năm kinh nghiệm ({actual_years} năm so với {experience_requirement} năm).")
    if not pros:
        pros = ["CV có một số kỹ năng cơ bản phù hợp với mô tả công việc."]
        
    cons = []
    if missing_skills:
        cons.append(f"Thiếu các kỹ năng bắt buộc: {', '.join(missing_skills[:5])}.")
    if actual_years < experience_requirement:
        cons.append(f"Chưa đạt số năm kinh nghiệm tối thiểu {experience_requirement} năm (phát hiện {actual_years} năm).")
        
    return CVEvaluationSchema(
        total_score=total_score,
        skills_match=skills_match,
        experience_match=f"Phát hiện {actual_years} năm kinh nghiệm. Yêu cầu tối thiểu {experience_requirement} năm.",
        pros=pros,
        cons=cons,
        fit_status=fit_status,
    )


def evaluate_cv_against_jd(cv_text: str, jd_criteria: dict) -> CVEvaluationSchema:
    print(f"[AI EVALUATION] ===== AI đánh giá bắt đầu. CV length={len(cv_text)}, JD skills={jd_criteria.get('required_skills', [])} =====")
    logger.info(f"[AI EVALUATION] Bắt đầu đánh giá CV. CV length={len(cv_text)}")
    # 1. Run pre-matching layer
    pre_match = pre_match_cv_with_jd(cv_text, jd_criteria)

    # 2. Check Cache
    cache_key = f"cv_eval_{cv_text}_{json.dumps(jd_criteria, sort_keys=True)}"
    cached = get_cached_response(cache_key)
    if cached:
        try:
            result = CVEvaluationSchema(**json.loads(cached))
            print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Cache hit). Score: {result.total_score} | Fit: {result.fit_status} =====")
            logger.info(f"[AI EVALUATION] Kết thúc (cache). Score={result.total_score}")
            return result
        except Exception:
            pass

    if not _get_api_key():
        print("[AI EVALUATION] Không có API key – dùng local scoring fallback")
        res = _score_cv_locally(cv_text, jd_criteria, pre_match)
        set_cached_response(cache_key, res.model_dump_json())
        print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Local Fallback). Score: {res.total_score} | Fit: {res.fit_status} =====")
        logger.info(f"[AI EVALUATION] Kết thúc (local fallback). Score={res.total_score}")
        return res

    prompt = f"""
    Bạn là một Tech Recruiter / Chuyên gia đánh giá ứng viên cao cấp.
    Hãy đối chiếu hồ sơ (CV) của ứng viên với Tiêu chí tuyển dụng (JD Criteria) được cung cấp dưới đây để chấm điểm và đưa ra nhận xét chi tiết, khách quan, không định kiến.

    Dưới đây là thông tin đối chiếu từ khóa và trích xuất sơ bộ (Matching Layer) được thực hiện bởi hệ thống trước khi dùng AI:
    - Ngành nghề được xác định: {pre_match['industry']}
    - Kỹ năng bắt buộc ĐÃ KHỚP: {', '.join(pre_match['matched_required_skills']) if pre_match['matched_required_skills'] else 'Không có'}
    - Kỹ năng bắt buộc THIẾU: {', '.join(pre_match['missing_required_skills']) if pre_match['missing_required_skills'] else 'Không có'}
    - Kỹ năng ưu tiên ĐÃ KHỚP: {', '.join(pre_match['matched_preferred_skills']) if pre_match['matched_preferred_skills'] else 'Không có'}
    - Số năm kinh nghiệm ước tính từ CV: {pre_match['detected_years_experience']} năm
    - Trạng thái khớp bằng cấp/học văn: {pre_match['education_match_status']}

    QUAN TRỌNG – Tiêu chí chấm điểm (tổng 100 điểm):
    - Kỹ năng kỹ thuật phù hợp JD (dựa trên kỹ năng đã khớp & thiếu): 50 điểm
    - **Kinh nghiệm làm việc thực tế** (số năm, dự án thực tế, môi trường làm việc): 25 điểm – ĐÂY LÀ TIÊU CHÍ QUAN TRỌNG
    - Kinh nghiệm/từ khóa thực hành: 15 điểm
    - Học vấn / bằng cấp: 10 điểm

    Khi đánh giá kinh nghiệm: xem xét số năm làm việc thực tế, tên công ty, dự án đã tham gia, không chỉ đơn thuần đếm năm.
    Nếu ứng viên có nhiều năm kinh nghiệm thực tế hơn yêu cầu, hãy cộng điểm thưởng.

    [TIÊU CHÍ TUYỂN DỤNG TỪ JD]:
    {jd_criteria}

    [NỘI DUNG NGUYÊN BẢN CỦA CV ỨNG VIÊN]:
    \"\"\"
    {cv_text}
    \"\"\"
    """

    print("[AI EVALUATION] Đang gọi Gemini API để đánh giá CV...")
    try:
        client = _get_client()
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        print(f"[AI EVALUATION] Gemini API đã phản hồi. Đang xử lý kết quả...")
        data = json.loads(response.text)
        payload = data.get("candidate_evaluation") if isinstance(data, dict) and "candidate_evaluation" in data else data
        payload = _normalize_evaluation_payload(payload if isinstance(payload, dict) else {})
        local_eval = _score_cv_locally(cv_text, jd_criteria, pre_match)

        if not payload:
            set_cached_response(cache_key, local_eval.model_dump_json())
            print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Local recovery – payload rỗng). Score: {local_eval.total_score} | Fit: {local_eval.fit_status} =====")
            logger.info(f"[AI EVALUATION] Kết thúc (local recovery). Score={local_eval.total_score}")
            return local_eval

        if payload.get("total_score", 0) == 0 and not payload.get("skills_match"):
            set_cached_response(cache_key, local_eval.model_dump_json())
            print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Local recovery – score=0). Score: {local_eval.total_score} | Fit: {local_eval.fit_status} =====")
            logger.info(f"[AI EVALUATION] Kết thúc (local recovery score=0). Score={local_eval.total_score}")
            return local_eval

        if payload.get("total_score", 0) <= 20 and local_eval.total_score > payload.get("total_score", 0):
            set_cached_response(cache_key, local_eval.model_dump_json())
            print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Local override – Gemini score quá thấp). Score: {local_eval.total_score} | Fit: {local_eval.fit_status} =====")
            logger.info(f"[AI EVALUATION] Kết thúc (local override). Score={local_eval.total_score}")
            return local_eval

        final_schema = CVEvaluationSchema(**payload)
        set_cached_response(cache_key, final_schema.model_dump_json())
        print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Gemini API). Score: {final_schema.total_score} | Fit: {final_schema.fit_status} =====")
        logger.info(f"[AI EVALUATION] Kết thúc (Gemini API). Score={final_schema.total_score}")
        return final_schema
    except Exception as exc:
        import traceback
        print(f"[AI EVALUATION] Lỗi khi gọi Gemini API: {str(exc)}")
        print(f"[AI EVALUATION] Traceback:\n{traceback.format_exc()}")
        logger.exception("Gemini CV evaluation failed")
        res = _score_cv_locally(cv_text, jd_criteria, pre_match)
        set_cached_response(cache_key, res.model_dump_json())
        print(f"[AI EVALUATION] ===== AI đánh giá kết thúc (Exception fallback). Score: {res.total_score} | Fit: {res.fit_status} =====")
        logger.info(f"[AI EVALUATION] Kết thúc (exception fallback). Score={res.total_score}")
        return res