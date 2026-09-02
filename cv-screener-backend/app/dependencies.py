"""
Dependency injection cho xác thực (Authentication).

Cách dùng:
  Đặt ADMIN_API_KEY trong file .env
  Admin gọi endpoint bảo vệ phải gửi header: X-Admin-Key: <key>

Ví dụ:
  @router.delete("/{id}", dependencies=[Depends(require_admin)])
  def delete_job(...):
      ...
"""

import os
import logging
from fastapi import Depends, Header, HTTPException, status

logger = logging.getLogger(__name__)


def require_admin(x_admin_key: str = Header(..., description="Admin API key (header: X-Admin-Key)")):
    """
    Dependency bảo vệ các endpoint dành riêng cho nhà tuyển dụng/admin.
    Client phải gửi header: X-Admin-Key: <ADMIN_API_KEY từ .env>

    Nếu ADMIN_API_KEY chưa cấu hình trong .env, dependency này bị bỏ qua
    (dev mode) và log cảnh báo.
    """
    expected_key = os.getenv("ADMIN_API_KEY", "").strip()

    if not expected_key:
        # Dev mode: chưa cấu hình key → cho phép tất cả nhưng cảnh báo
        logger.warning(
            "[AUTH] ADMIN_API_KEY chưa được cấu hình trong .env. "
            "Tất cả request admin được chấp nhận (DEV MODE). "
            "Vui lòng đặt ADMIN_API_KEY trước khi deploy lên production."
        )
        return

    if x_admin_key != expected_key:
        logger.warning(f"[AUTH] Yêu cầu admin bị từ chối – key không hợp lệ.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Không có quyền truy cập. Vui lòng cung cấp Admin API Key hợp lệ qua header X-Admin-Key.",
        )
