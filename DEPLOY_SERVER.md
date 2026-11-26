# HƯỚNG DẪN DEPLOY TCEX SIMULATE ENGINE TRÊN SERVER VỚI DOCKER

Tài liệu này hướng dẫn chi tiết cách đưa mã nguồn từ repository **`simulate-tcbx`** lên server Linux (ví dụ: `13.213.156.53`), cấu hình file bảo mật và khởi chạy hệ thống bằng Docker Compose.

---

## 1. Yêu cầu trên Server
- Hệ điều hành: Ubuntu 20.04 / 22.04 LTS hoặc Linux tương thích.
- Cài đặt Docker & Docker Compose:
  ```bash
  sudo apt-get update
  sudo apt-get install -y docker.io docker-compose-plugin git
  sudo systemctl enable --now docker
  # Thêm user vào group docker nếu không muốn gõ sudo:
  sudo usermod -aG docker $USER && newgrp docker
  ```

---

## 2. Các bước triển khai

### Bước 1: Clone mã nguồn từ GitHub
Đăng nhập vào server và clone repo:
```bash
git clone https://github.com/tramee2109/simulate-tcbx.git
cd simulate-tcbx
```

### Bước 2: Tải file danh sách tài khoản (`accounts.csv`) lên Server
Do các file chứa API keys được chặn trên Git theo chính sách bảo mật, bạn cần copy file tài khoản lên server vào thư mục dự án:
```bash
# Từ máy tính của bạn (PowerShell):
scp -i ~/.ssh/id_ed25519 "E:\My\the20\simulate-sdk\new-temp-accounts-global (1).csv" ubuntu@13.213.156.53:~/simulate-tcbx/accounts.csv
```
*(Hoặc dùng nano/vi trên server để tạo file `accounts.csv` và dán nội dung danh sách 20 tài khoản vào)*.

### Bước 3: Tạo file cấu hình môi trường `.env`
Sao chép từ `.env.example`:
```bash
cp .env.example .env
nano .env
```
Nội dung cơ bản trong `.env`:
```env
TCEX_BASE_URL=https://simulation.the20.sg
TCEX_SESSION_KEY=dc1tpbu76rkff8gccfug
TCEX_MARKET_SYMBOL=BTC_VND

# Chế độ chạy: LIVE (đặt lệnh thực) hoặc PAPER (giả lập an toàn)
TCEX_EXECUTION_MODE=LIVE
TCEX_ALLOW_LIVE=true

TCEX_TICK_INTERVAL=2.0
TCEX_SNAPSHOT_INTERVAL=1800
HOST_ACCOUNT_CSV=./accounts.csv
```

### Bước 4: Tạo các thư mục lưu trữ dữ liệu (logs, data, reports)
```bash
mkdir -p logs data reports
```

### Bước 5: Build và Khởi chạy Engine với Docker Compose
```bash
# Build image và chạy container ở chế độ background
docker compose up -d --build
```

---

## 3. Các lệnh quản lý & kiểm tra vận hành

### Xem log thời gian thực:
```bash
# Xem log chung của Docker
docker compose logs -f simulate-engine

# Xem log chi tiết từng lệnh đặt vào sàn
tail -f logs/orders.log

# Xem log kiểm soát rủi ro
tail -f logs/audit_events.log
```

### Kiểm tra trạng thái Container:
```bash
docker compose ps
```

### Kiểm tra báo cáo Balance Snapshot:
Snapshot được xuất tự động mỗi 30 phút:
```bash
cat reports/balance_snapshot_latest.json
```

### Chạy kiểm tra số dư ngay lập tức bằng script trong container:
```bash
docker compose exec simulate-engine python local/check_balance.py
```

### Dừng hoặc khởi động lại Engine:
```bash
# Dừng container an toàn (engine sẽ chụp snapshot lần cuối trước khi tắt)
docker compose stop

# Khởi động lại
docker compose restart

# Tắt và xóa container
docker compose down
```
