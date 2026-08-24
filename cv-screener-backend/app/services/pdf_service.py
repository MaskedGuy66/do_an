import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pypdf


def extract_text_from_pdf(file_path: str) -> str:
    """Đọc file PDF và trả về toàn bộ text dạng plain text."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file tại: {file_path}")

    text = ""
    try:
        with open(file_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
    except Exception as exc:
        raise RuntimeError(f"Lỗi khi trích xuất PDF: {exc}") from exc

    return text.strip()


def extract_text_from_docx(file_path: str) -> str:
    """Trích xuất text từ file .docx bằng cách đọc XML trong gói nén."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file tại: {file_path}")

    try:
        with zipfile.ZipFile(file_path) as zf:
            xml_content = zf.read("word/document.xml")
    except Exception as exc:
        raise RuntimeError(f"Lỗi khi đọc DOCX: {exc}") from exc

    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    root = ET.fromstring(xml_content)
    paragraphs = []

    for paragraph in root.findall(".//w:p", ns):
        texts = []
        for text_node in paragraph.findall(".//w:t", ns):
            if text_node.text:
                texts.append(text_node.text)
        if texts:
            paragraphs.append("".join(texts))

    return "\n".join(paragraphs).strip()


def extract_text_from_file(file_path: str) -> str:
    """Trích xuất text từ các file PDF, DOCX, TXT và trả về nội dung plain text."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Không tìm thấy file tại: {file_path}")

    suffix = path.suffix.lower()

    if suffix in {".txt", ".md", ".rtf"}:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()

    if suffix == ".pdf":
        return extract_text_from_pdf(str(path))

    if suffix == ".docx":
        return extract_text_from_docx(str(path))

    if suffix in {".png", ".jpg", ".jpeg"}:
        return ""

    raise ValueError(f"Định dạng file không được hỗ trợ: {suffix}")