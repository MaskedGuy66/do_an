import chromadb
from chromadb.config import Settings

# Khởi tạo ChromaDB client lưu dữ liệu trực tiếp vào thư mục .chroma/
chroma_client = chromadb.PersistentClient(path="./.chroma")

def get_vector_collection():
    # Tạo hoặc lấy lại collection tên là "cv_collection"
    # Dùng khoảng cách Cosine để đo độ tương đồng giữa CV và JD
    collection = chroma_client.get_or_create_collection(
        name="cv_collection", 
        metadata={"hnsw:space": "cosine"}
    )
    return collection