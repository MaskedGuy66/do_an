#!/usr/bin/env python3
"""Comprehensive test script for CV Screener API - All endpoints"""

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
    CYAN = '\033[96m'
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

def print_test_result(test_num, endpoint, status_code, expected_code):
    if status_code == expected_code:
        print_success(f"Test {test_num}: {endpoint} [{status_code}]")
        return True
    else:
        print_error(f"Test {test_num}: {endpoint} [{status_code}] (Expected: {expected_code})")
        return False

# Test counters
total_tests = 0
passed_tests = 0

print(f"{Colors.CYAN}╔═══════════════════════════════════════════════════════════════════╗")
print(f"║         CV SCREENER API - COMPREHENSIVE TEST SUITE                  ║")
print(f"║              Testing GIAI DOẠN 2 - Core System                       ║")
print(f"╚═══════════════════════════════════════════════════════════════════╝{Colors.END}\n")

# ============================================================================
# SECTION 1: JD MANAGEMENT
# ============================================================================
print_header("SECTION 1: JD MANAGEMENT")

# Test 1.1: Ingest JD (Text)
test_num = 1
print(f"Test {test_num}: POST /api/v1/jd/ingest")
jd_payload = {
    "title": "Senior Python Backend Engineer",
    "raw_text": "Tuyển dụng lập trình viên Python từ 3 năm kinh nghiệm. Yêu cầu: FastAPI, PostgreSQL, Docker, Redis. Bằng Thạc sĩ CNTT. Trách nhiệm: Phát triển API, thiết kế database, quản lý server. Làm việc với AWS."
}

jd_id = None
try:
    response = requests.post(f"{api_base}/jd/ingest", json=jd_payload, timeout=15)
    total_tests += 1
    if print_test_result(test_num, "POST /jd/ingest", response.status_code, 201):
        passed_tests += 1
        jd_response = response.json()
        jd_id = jd_response.get("jd_id")
        print_info(f"Created JD ID: {jd_id}")
        print_info(f"Extracted skills: {jd_response.get('extracted_criteria', {}).get('required_skills', [])}")
    else:
        print_error(f"Response: {response.text}")
except Exception as e:
    total_tests += 1
    print_error(f"Error: {str(e)}")

# Test 1.2: List all JDs
test_num += 1
print(f"\nTest {test_num}: GET /api/v1/jd")
try:
    response = requests.get(f"{api_base}/jd", timeout=5)
    total_tests += 1
    if print_test_result(test_num, "GET /jd", response.status_code, 200):
        passed_tests += 1
        jd_list = response.json()
        print_info(f"Total JDs: {jd_list.get('total', 0)}")
        print_info(f"Current batch: {len(jd_list.get('data', []))} items")
    else:
        print_error(f"Response: {response.text}")
except Exception as e:
    total_tests += 1
    print_error(f"Error: {str(e)}")

# Test 1.3: Get JD detail
if jd_id:
    test_num += 1
    print(f"\nTest {test_num}: GET /api/v1/jd/{jd_id}")
    try:
        response = requests.get(f"{api_base}/jd/{jd_id}", timeout=5)
        total_tests += 1
        if print_test_result(test_num, f"GET /jd/{jd_id}", response.status_code, 200):
            passed_tests += 1
            jd_detail = response.json()
            print_info(f"Title: {jd_detail.get('title')}")
            print_info(f"Criteria: {json.dumps(jd_detail.get('extracted_criteria'), indent=2, ensure_ascii=False)[:100]}...")
        else:
            print_error(f"Response: {response.text}")
    except Exception as e:
        total_tests += 1
        print_error(f"Error: {str(e)}")

# ============================================================================
# SECTION 2: CV MANAGEMENT
# ============================================================================
print_header("SECTION 2: CV MANAGEMENT")

# Test 2.1: Upload CV
test_num += 1
print(f"Test {test_num}: POST /api/v1/cv/upload")

test_pdf_path = "test_cv.pdf"
cv_id = None

if os.path.exists(test_pdf_path):
    try:
        with open(test_pdf_path, "rb") as f:
            files = {"file": ("test_cv.pdf", f, "application/pdf")}
            response = requests.post(f"{api_base}/cv/upload", files=files, timeout=15)
        
        total_tests += 1
        if print_test_result(test_num, "POST /cv/upload", response.status_code, 201):
            passed_tests += 1
            cv_response = response.json()
            cv_id = cv_response.get("cv_id")
            print_info(f"Uploaded CV ID: {cv_id}")
            print_info(f"Text length: {cv_response.get('text_length', 0)} characters")
        else:
            print_error(f"Response: {response.text}")
    except Exception as e:
        total_tests += 1
        print_error(f"Error: {str(e)}")
else:
    total_tests += 1
    print_error(f"Test file not found: {test_pdf_path}")

# Test 2.2: List all CVs
test_num += 1
print(f"\nTest {test_num}: GET /api/v1/cv")
try:
    response = requests.get(f"{api_base}/cv", timeout=5)
    total_tests += 1
    if print_test_result(test_num, "GET /cv", response.status_code, 200):
        passed_tests += 1
        cv_list = response.json()
        print_info(f"Total CVs: {cv_list.get('total', 0)}")
        print_info(f"Current batch: {len(cv_list.get('data', []))} items")
    else:
        print_error(f"Response: {response.text}")
except Exception as e:
    total_tests += 1
    print_error(f"Error: {str(e)}")

# Test 2.3: Get CV detail
if cv_id:
    test_num += 1
    print(f"\nTest {test_num}: GET /api/v1/cv/{cv_id}")
    try:
        response = requests.get(f"{api_base}/cv/{cv_id}", timeout=5)
        total_tests += 1
        if print_test_result(test_num, f"GET /cv/{cv_id}", response.status_code, 200):
            passed_tests += 1
            cv_detail = response.json()
            print_info(f"Status: {cv_detail.get('status')}")
            print_info(f"Score: {cv_detail.get('total_score')}")
        else:
            print_error(f"Response: {response.text}")
    except Exception as e:
        total_tests += 1
        print_error(f"Error: {str(e)}")

# ============================================================================
# SECTION 3: EVALUATION
# ============================================================================
print_header("SECTION 3: EVALUATION")

# Test 3.1: Evaluate CV against JD
if cv_id and jd_id:
    test_num += 1
    print(f"Test {test_num}: POST /api/v1/cv/{cv_id}/evaluate/{jd_id}")
    try:
        response = requests.post(f"{api_base}/cv/{cv_id}/evaluate/{jd_id}", timeout=30)
        total_tests += 1
        if print_test_result(test_num, f"POST /cv/{cv_id}/evaluate/{jd_id}", response.status_code, 200):
            passed_tests += 1
            eval_result = response.json()
            print_info(f"Score: {eval_result.get('score')}")
            print_info(f"Fit status: {eval_result.get('fit_status')}")
            print_success("Evaluation completed successfully!")
        else:
            print_error(f"Response: {response.text}")
    except Exception as e:
        total_tests += 1
        print_error(f"Error: {str(e)}")
else:
    print_error("Cannot test evaluation: Missing CV or JD")

# ============================================================================
# SECTION 4: INPUT VALIDATION
# ============================================================================
print_header("SECTION 4: INPUT VALIDATION")

# Test 4.1: Upload invalid file format
test_num += 1
print(f"Test {test_num}: POST /api/v1/cv/upload (Invalid format)")
try:
    # Create a non-PDF file
    with open("test_file.txt", "w") as f:
        f.write("This is not a PDF")
    
    with open("test_file.txt", "rb") as f:
        files = {"file": ("test_file.txt", f, "text/plain")}
        response = requests.post(f"{api_base}/cv/upload", files=files, timeout=5)
    
    total_tests += 1
    if response.status_code == 400:
        passed_tests += 1
        print_success(f"Test {test_num}: Correctly rejected invalid format [400]")
    else:
        print_error(f"Test {test_num}: Expected 400, got {response.status_code}")
    
    os.remove("test_file.txt")
except Exception as e:
    total_tests += 1
    print_error(f"Error: {str(e)}")

# Test 4.2: Ingest JD with empty text
test_num += 1
print(f"\nTest {test_num}: POST /api/v1/jd/ingest (Empty text)")
try:
    invalid_jd = {
        "title": "Test",
        "raw_text": ""
    }
    response = requests.post(f"{api_base}/jd/ingest", json=invalid_jd, timeout=5)
    
    total_tests += 1
    if response.status_code == 400:
        passed_tests += 1
        print_success(f"Test {test_num}: Correctly rejected empty text [400]")
    else:
        print_error(f"Test {test_num}: Expected 400, got {response.status_code}")
except Exception as e:
    total_tests += 1
    print_error(f"Error: {str(e)}")

# ============================================================================
# SUMMARY
# ============================================================================
print(f"\n{Colors.CYAN}{'='*70}")
print(f"TEST SUMMARY")
print(f"{'='*70}{Colors.END}")

pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
print_info(f"Total Tests: {total_tests}")
print_info(f"Passed: {passed_tests}")
print_info(f"Failed: {total_tests - passed_tests}")
print_info(f"Pass Rate: {pass_rate:.1f}%")

if pass_rate == 100:
    print(f"\n{Colors.GREEN}🎉 ALL TESTS PASSED!{Colors.END}\n")
elif pass_rate >= 80:
    print(f"\n{Colors.YELLOW}⚠️  MOST TESTS PASSED (Some failures detected){Colors.END}\n")
else:
    print(f"\n{Colors.RED}❌ MULTIPLE FAILURES - REVIEW NEEDED{Colors.END}\n")
