#!/usr/bin/env python3
"""Generate a test CV PDF with actual text content"""

from fpdf import FPDF

def create_test_cv_pdf(output_path="test_cv.pdf"):
    """Create a sample CV PDF with text content"""
    
    pdf = FPDF()
    pdf.add_page()
    
    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Nguyen Van A - Senior Python Developer", ln=True)
    
    # Personal Info
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "PERSONAL INFORMATION", ln=True)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Email: nguyenvana@example.com", ln=True)
    pdf.cell(0, 6, "Phone: +84 912 345 678", ln=True)
    pdf.cell(0, 6, "Address: Ho Chi Minh City, Vietnam", ln=True)
    pdf.ln(5)
    
    # Experience
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "WORK EXPERIENCE", ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Senior Python Developer (2022-2024)", ln=True)
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "- Developed and maintained FastAPI backend services", ln=True)
    pdf.cell(0, 5, "- Implemented PostgreSQL database optimization", ln=True)
    pdf.cell(0, 5, "- Deployed applications on AWS using Docker and Kubernetes", ln=True)
    pdf.cell(0, 5, "- Worked with Redis for caching and session management", ln=True)
    pdf.ln(3)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Python Developer (2020-2022)", ln=True)
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "- Built RESTful APIs using Python and Flask", ln=True)
    pdf.cell(0, 5, "- Designed and optimized MySQL databases", ln=True)
    pdf.cell(0, 5, "- Implemented automated testing with pytest", ln=True)
    pdf.ln(5)
    
    # Skills
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "TECHNICAL SKILLS", ln=True)
    
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 6, "Languages: Python, JavaScript, TypeScript, SQL, Java, Go", ln=True)
    pdf.cell(0, 6, "Backend: FastAPI, Node.js, Django, Flask, GraphQL", ln=True)
    pdf.cell(0, 6, "Databases: PostgreSQL, MySQL, MongoDB, Redis", ln=True)
    pdf.cell(0, 6, "DevOps: Docker, Kubernetes, AWS, GitHub Actions, CI/CD", ln=True)
    pdf.cell(0, 6, "Frontend: React, Vue.js, TypeScript, HTML5, CSS3", ln=True)
    pdf.ln(5)
    
    # Education
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "EDUCATION", ln=True)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Master of Science in Computer Science", ln=True)
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "University of Technology, Vietnam (2018-2020)", ln=True)
    pdf.ln(2)
    
    pdf.set_font("Arial", "B", 10)
    pdf.cell(0, 6, "Bachelor of Science in Information Technology", ln=True)
    
    pdf.set_font("Arial", "", 9)
    pdf.cell(0, 5, "National University of Vietnam (2014-2018)", ln=True)
    
    pdf.output(output_path)
    print(f"✅ Test CV PDF created: {output_path}")

if __name__ == "__main__":
    create_test_cv_pdf()
