#!/usr/bin/env python3
"""Test CV Upload with proper PDF"""

import requests
import json
import os

base_url = "http://127.0.0.1:8000"
api_base = f"{base_url}/api/v1"

# Color codes
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.END}")

# Test PDF Upload
print(f"\n{Colors.BLUE}{'='*70}")
print("TEST: POST /api/v1/cv/upload - Upload CV (PDF with text)")
print(f"{'='*70}{Colors.END}\n")

test_pdf_path = "test_cv.pdf"

if not os.path.exists(test_pdf_path):
    print_error(f"PDF file not found: {test_pdf_path}")
    print_info("Please run: poetry run python create_test_cv.py")
else:
    file_size = os.path.getsize(test_pdf_path)
    print_info(f"PDF file found: {test_pdf_path} ({file_size} bytes)")
    
    try:
        with open(test_pdf_path, "rb") as f:
            files = {"file": ("test_cv.pdf", f, "application/pdf")}
            response = requests.post(f"{api_base}/cv/upload", files=files, timeout=15)
        
        print_success(f"Status: {response.status_code}")
        
        if response.status_code == 201:
            cv_response = response.json()
            print(json.dumps(cv_response, indent=2, ensure_ascii=False))
            cv_id = cv_response.get("cv_id")
            print_success(f"Uploaded CV with ID: {cv_id}")
            print_success(f"Extracted text preview:\n{cv_response.get('extracted_text_preview')}")
        else:
            print_error(f"Response: {response.text}")
            
    except Exception as e:
        print_error(f"Error: {str(e)}")

print(f"\n{Colors.BLUE}{'='*70}")
print("SUMMARY: PDF Upload Test")
print(f"{'='*70}{Colors.END}\n")
