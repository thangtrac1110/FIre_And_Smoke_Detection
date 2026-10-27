# Fire and Smoke Detection

Ứng dụng web phát hiện **lửa và khói theo thời gian thực** bằng mô hình YOLO (Ultralytics), giao diện viết bằng Flask. Video được nhận dạng từng khung hình, vẽ khung bao quanh vùng có lửa/khói và hiển thị thống kê trực tiếp trên trình duyệt.

## Tính năng

- Nhiều nguồn video:
  - Webcam của máy
  - Camera IP (ví dụ app **IP Webcam** trên điện thoại)
  - File video tải lên
  - Luồng camera công khai (MJPEG)
- Điều chỉnh ngưỡng **confidence** và **IoU** ngay trong lúc chạy
- Bảng thông số trực tiếp: FPS, tổng số đối tượng phát hiện, số lượng theo từng lớp, độ tin cậy thấp nhất

## Cấu trúc thư mục

```
├── app.py            # Flask server: các route stream, upload, metrics
├── captures.py       # Các lớp đọc nguồn video (OpenCV, HLS qua FFmpeg)
├── config.yaml       # Cấu hình model, camera, server
├── requirements.txt
├── models/
│   ├── best.pt       # Trọng số đã huấn luyện cho lửa/khói (được dùng mặc định)
│   └── yolo26n.pt    # Trọng số YOLO gốc
├── static/           # CSS, JS, hình ảnh
├── templates/
│   └── index.html    # Giao diện chính
└── uploads/          # Video tải lên và video mẫu để thử
```

## Cài đặt

Yêu cầu Python 3.10 trở lên.

```bash
git clone https://github.com/thangtrac1110/FIre_And_Smoke_Detection.git
cd FIre_And_Smoke_Detection

python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

## Chạy ứng dụng

```bash
python app.py
```

Mở trình duyệt tại **http://localhost:5000**, chọn nguồn video rồi bấm bắt đầu.

Để thử nhanh mà không cần camera, chọn nguồn **File** và dùng một trong các video mẫu có sẵn trong thư mục `uploads/`.

## Cấu hình

Chỉnh trong `config.yaml`:

| Khóa | Ý nghĩa |
|---|---|
| `model.path` | Đường dẫn file trọng số YOLO |
| `ip_webcam.default_url` | Địa chỉ mặc định của camera IP, ví dụ `http://<ip-điện-thoại>:8080/video` |
| `public_camera.default_stream_url` | Luồng camera công khai mặc định |
| `server.host`, `server.port` | Địa chỉ và cổng chạy server |
| `server.debug` | Bật chế độ debug của Flask (nên tắt khi triển khai) |

## API

| Route | Phương thức | Mô tả |
|---|---|---|
| `/video_feed?source=webcam\|ip\|file\|public` | GET | Luồng MJPEG đã được nhận dạng |
| `/upload` | POST | Tải video lên (trường `video`) |
| `/update_params?conf=&iou=` | POST | Cập nhật ngưỡng nhận dạng |
| `/metrics` | GET | Thông số hiện tại dạng JSON |
| `/check_stream?url=` | GET | Kiểm tra camera IP có kết nối được không |
| `/stop_stream` | POST | Dừng luồng hiện tại |

## Ghi công

Mã nguồn ban đầu từ [NhanPhan090806/FIre_And_Smoke_Detection](https://github.com/NhanPhan090806/FIre_And_Smoke_Detection).
