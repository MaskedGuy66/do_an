import pandas as pd
import re
from collections import Counter

df = pd.read_csv('data.csv')
text = " ".join(df['Description'].astype(str).tolist()).lower()

# Normalize text spaces
text = re.sub(r'\s+', ' ', text)

# Map of skill category to candidates derived from dataset scanning
extracted_dict = {
    # 1. Databases & SQL
    "sql": ["sql", "t-sql", "tsql", "pl/sql", "plsql", "sqlite"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mysql": ["mysql", "my sql"],
    "oracle": ["oracle", "oracle database", "pl/sql"],
    "sql server": ["sql server", "mssql", "microsoft sql server", "ssis", "ssrs", "ssas"],
    "snowflake": ["snowflake"],
    "bigquery": ["bigquery", "google bigquery"],
    "redshift": ["redshift", "amazon redshift"],
    "mongodb": ["mongodb", "mongo"],
    "nosql": ["nosql", "non-relational database", "document store"],
    "redis": ["redis", "in-memory database"],
    "database": ["database", "cơ sở dữ liệu", "csdl", "qlcsdl", "sql", "nosql", "datastore", "rdbms", "database management"],

    # 2. Data Visualization & BI Tools
    "power bi": ["power bi", "powerbi", "pbi", "dax", "power query", "power pivot"],
    "tableau": ["tableau", "tableau desktop", "tableau server", "tableau prep"],
    "excel": ["excel", "microsoft excel", "vba", "pivot tables", "vlookup", "index match", "advanced excel"],
    "looker": ["looker", "lookml"],
    "alteryx": ["alteryx"],
    "qlik": ["qlik", "qlikview", "qliksense"],
    "sas": ["sas", "sas enterprise"],
    "spss": ["spss", "pasw"],
    "stata": ["stata"],

    # 3. Data Engineering & Cloud Data Platforms
    "etl": ["etl", "elt", "data extraction", "data transformation", "data loading", "ssis", "data pipeline", "data pipelines", "pipeline development"],
    "data warehousing": ["data warehouse", "data warehousing", "edw", "enterprise data warehouse", "star schema", "snowflake schema", "data mart"],
    "data governance": ["data governance", "data stewardship", "data lineage", "data dictionary", "data quality", "data catalog"],
    "data modeling": ["data modeling", "data model", "data modeling concepts", "dimensional modeling", "er diagram", "er-diagram"],
    "data architecture": ["data architecture", "data architect"],
    "azure": ["azure", "azure data factory", "adf", "azure synapse", "azure databricks"],
    "aws": ["aws", "amazon web services", "redshift", "s3", "glue", "athena", "lambda"],
    "gcp": ["gcp", "google cloud", "google cloud platform", "bigquery"],
    "hadoop": ["hadoop", "hdfs", "hive", "pig"],
    "spark": ["spark", "pyspark", "apache spark"],
    "databricks": ["databricks"],
    "airflow": ["airflow", "apache airflow"],
    "kafka": ["kafka", "apache kafka"],

    # 4. Programming Languages & Frameworks
    "python": ["python", "py", "django", "flask", "fastapi", "numpy", "pandas", "scipy", "statsmodels", "pyspark"],
    "r": ["r", "rstudio", "ggplot2", "dplyr"],
    "javascript": ["javascript", "js", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "react": ["react", "reactjs", "react.js"],
    "node": ["node", "nodejs", "node.js"],
    "java": ["java", "spring", "springboot", "spring boot"],
    "c#": ["c#", "csharp", "net", "dot net", "dotnet"],
    "go": ["go", "golang"],
    "linux": ["linux", "ubuntu", "unix", "centos", "redhat", "shell", "bash"],
    "graphql": ["graphql", "gql"],
    "fastapi": ["fastapi", "api rest", "rest api", "fast api"],
    "api": ["api", "rest api", "restful api", "backend api", "web service", "graphql", "microservices"],

    # 5. Data Science, AI & Analytics Concepts
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

    # 6. Enterprise Systems & Domain Software
    "salesforce": ["salesforce", "sfdc", "salesforce crm"],
    "sap": ["sap", "sap bw", "sap hana", "sap erp"],
    "workday": ["workday"],
    "hubspot": ["hubspot"],
    "epic": ["epic", "epic systems", "ehr", "emr"],
    "cerner": ["cerner"],
    "gis": ["gis", "arcgis", "qgis", "geographic information system"],
    "jira": ["jira", "confluence", "atlassian"],
    "git": ["git", "github", "gitlab", "bitbucket"],

    # 7. DevOps & Software Engineering
    "docker": ["docker", "container", "containers", "containerization"],
    "kubernetes": ["kubernetes", "k8s"],
    "devops": ["devops", "ci/cd", "continuous integration"],
    "backend": ["backend", "back-end", "server-side", "server side"],
    "system deployment": ["triển khai hệ thống", "deploy hệ thống", "deployment", "devops", "system deployment", "ci/cd"],

    # 8. Business & Management / Non-Tech Domains
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

print(f"Total skills defined in expanded SKILL_ALIASES: {len(extracted_dict)}")

# Verify match occurrences in dataset
total_matches = 0
for skill, aliases in extracted_dict.items():
    matched = False
    for alias in aliases:
        pattern = r'\b' + re.escape(alias) + r'\b'
        c = len(re.findall(pattern, text))
        if c > 0:
            matched = True
            total_matches += c
print(f"Verified alias dataset occurrences count total: {total_matches}")
