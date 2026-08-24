import pandas as pd
import re
from collections import Counter

df = pd.read_csv('../data.csv')
text = " ".join(df['Description'].astype(str).tolist()).lower()

# 1. Unigram & Bigram extraction for frequent tech/domain phrases
words = re.findall(r'\b[a-z0-9\+\#\.\-]{2,}\b', text)

# Stopwords to filter out non-skills
stopwords = set([
    'and', 'to', 'the', 'of', 'in', 'with', 'for', 'or', 'is', 'experience', 'our', 'business',
    'as', 'we', 'work', 'on', 'will', 'be', 'that', 'are', 'this', 'skills', 'you', 'an', 'at',
    'team', 'support', 'ability', 'by', 'other', 'all', 'including', 'job', 'from', 'position',
    'your', 'role', 'required', 'strong', 'tools', 'requirements', 'must', 'have', 'years', 'working',
    'new', 'such', 'more', 'their', 'benefits', 'equal', 'opportunity', 'employer', 'pay', 'range',
    'salary', 'full-time', 'part-time', 'schedule', 'location', 'person', 'remote', 'hybrid', 'status',
    'gender', 'race', 'color', 'religion', 'sex', 'national', 'origin', 'disability', 'veteran',
    'protected', 'state', 'city', 'year', 'per', 'hour', 'hourly', 'day', 'time', 'monday', 'friday',
    'applicant', 'applicants', 'employment', 'company', 'services', 'solutions', 'clients', 'management',
    'analysis', 'data', 'information', 'reporting', 'reports', 'analytics', 'analyst', 'health', 'care',
    'quality', 'systems', 'system', 'processes', 'process', 'project', 'projects', 'operations', 'operational',
    'technical', 'technology', 'technologies', 'development', 'develop', 'developing', 'design', 'create',
    'maintain', 'provide', 'ensure', 'help', 'use', 'using', 'used', 'understand', 'understanding',
    'knowledge', 'degree', 'bachelor', 'bachelors', 'master', 'masters', 'degree', 'education', 'preferred',
    'requirements', 'qualification', 'qualifications', 'duties', 'responsibilities', 'key', 'overview'
])

filtered_words = [w for w in words if w not in stopwords and not w.isdigit()]
word_counts = Counter(filtered_words).most_common(100)

print("--- Top 50 Potential Skill Keywords ---")
for w, c in word_counts[:50]:
    print(f"{w}: {c}")

# Search common tech / tool terms
tech_terms = [
    'sql', 'excel', 'python', 'power bi', 'powerbi', 'tableau', 'r', 'sas', 'spss', 'stata',
    'azure', 'aws', 'gcp', 'snowflake', 'bigquery', 'redshift', 'hadoop', 'spark', 'pyspark',
    'oracle', 'postgres', 'postgresql', 'mysql', 'mongodb', 'nosql', 'redis', 'jira', 'confluence',
    'sap', 'salesforce', 'workday', 'alteryx', 'qlik', 'looker', 'dax', 'vba', 'etl', 'elt',
    'git', 'docker', 'kubernetes', 'scrum', 'agile', 'devops', 'ssis', 'ssrs', 'ssas',
    'machine learning', 'deep learning', 'ai', 'nlp', 'statistical', 'statistics', 'mathematics',
    'economics', 'finance', 'accounting', 'marketing', 'sales', 'crm', 'erp', 'b2b', 'healthcare',
    'hipaa', 'epic', 'cerner', 'gis', 'arcgis', 'bi', 'business intelligence'
]

print("\n--- Industry Skill Frequencies ---")
for term in tech_terms:
    pattern = r'\b' + re.escape(term) + r'\b'
    matches = len(re.findall(pattern, text))
    if matches > 0:
        print(f"{term}: {matches}")
