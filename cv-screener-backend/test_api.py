#!/usr/bin/env python3
"""Test script for CV Screener API endpoints"""

import requests
import json
import time
import os

base_url = "http://127.0.0.1:8000"
api_base = f"{base_url}/api/v1"

# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"TEST: {text}")
    print(f"{'='*70}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

# Test 1: Health Check
print_header("GET / - Health Check")
try:
    response = requests.get(f"{base_url}/", timeout=5)
    print_success(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print_error(f"Error: {str(e)}")

# Test 2: Ingest JD
print_header("POST /api/v1/jd/ingest - Ingest Job Description (Text)")
try:
    jd_payload = {
        "title": "Python Backend Developer",
        "raw_text": "Tuyển dụng lập trình viên Python từ 3 năm kinh nghiệm. Yêu cầu: FastAPI, PostgreSQL, Docker, Redis. Bằng Thạc sĩ CNTT. Trách nhiệm: Phát triển API, thiết kế database, quản lý server."
    }
    print_info(f"Payload: {json.dumps(jd_payload, indent=2, ensure_ascii=False)}")
    
    response = requests.post(f"{api_base}/jd/ingest", json=jd_payload, timeout=15)
    print_success(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        jd_response = response.json()
        print(json.dumps(jd_response, indent=2, ensure_ascii=False))
        jd_id = jd_response.get("jd_id")
        print_success(f"Created JD with ID: {jd_id}")
    else:
        print_error(f"Response: {response.text}")
        
except Exception as e:
    print_error(f"Error: {str(e)}")

# Test 3: Test PDF Upload (we'll create a simple test PDF)
print_header("POST /api/v1/cv/upload - Upload CV (PDF)")
try:
    # Create a simple test PDF with reportlab or pypdf (since it's already installed)
    from pypdf import PdfWriter
    
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    
    test_pdf_path = "test_cv.pdf"
    with open(test_pdf_path, "wb") as f:
        writer.write(f)
    
    print_info(f"Created test PDF at: {test_pdf_path}")
    
    with open(test_pdf_path, "rb") as f:
        files = {"file": ("test_cv.pdf", f, "application/pdf")}
        response = requests.post(f"{api_base}/cv/upload", files=files, timeout=15)
    
    print_success(f"Status: {response.status_code}")
    
    if response.status_code == 201:
        cv_response = response.json()
        print(json.dumps(cv_response, indent=2, ensure_ascii=False))
        cv_id = cv_response.get("cv_id")
        print_success(f"Uploaded CV with ID: {cv_id}")
    else:
        print_error(f"Response: {response.text}")
    
    # Clean up
    if os.path.exists(test_pdf_path):
        os.remove(test_pdf_path)
        
except Exception as e:
    print_error(f"Error: {str(e)}")

print_header("Test Summary")
print_info("All tests completed. Check output above for results.")
