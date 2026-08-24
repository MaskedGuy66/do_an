# Frontend UI cho CV Screener

Giao diện web gốc để upload JD và nhiều CV, đồng thời gọi backend API để chấm điểm và xếp hạng ứng viên.

## Chạy

Sau khi backend đang chạy:

```powershell
poetry run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Mở:

- http://127.0.0.1:8000/ui/

## Chức năng

- Upload JD bằng text hoặc file
- Upload nhiều CV cùng lúc
- Chấm điểm theo JD
- Hiển thị ranking ứng viên theo điểm số
- Lưu trạng thái trong localStorage

## Lưu ý

- Frontend này được serve từ cùng FastAPI app.
- Cần có `GEMINI_API_KEY` hợp lệ để AI scoring chính xác.
- Nếu không có key, hệ thống có thể fallback hoặc trả về dữ liệu mock/test mode.
