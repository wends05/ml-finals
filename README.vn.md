# Đồ án cuối kỳ - Hệ thống Chào hỏi Gia đình bằng Nhận diện Khuôn mặt

[English](README.md) | [Tiếng Việt](README.vn.md)

## Mô tả dự án

Một hệ thống chào hỏi thực hiện huấn luyện mô hình nhận diện khuôn mặt thông qua TensorFlow và Keras. Một bộ điều khiển ESP32 sau đó sẽ được sử dụng để gọi đến backend Python nhằm hiển thị tên của khuôn mặt đã được nhận diện trên giao diện kiosk (frontend).

## Công nghệ sử dụng (Tech Stack)

- Python
- TensorFlow
- Keras
- ESP32
- FastAPI (Backend)
- React (Vite) (Frontend)

## Hướng dẫn cài đặt và chạy

1. Đầu tiên, clone repository và di chuyển vào thư mục backend:

```bash
git clone <url-của-repo>
```

2. Cài đặt các thư viện cần thiết cho backend:

```bash
cd backend
pip install -r requirements.txt
```

Tùy chọn: Bạn có thể cài đặt các thư viện thông qua trình quản lý gói `uv`:

```bash
uv sync
```

3. Thu thập bộ dữ liệu (dataset) bằng cách làm theo các hướng dẫn khi chạy lệnh:

```bash
python backend/scripts/01a_collect_faces.py
```

Dữ liệu sau đó sẽ được lưu trữ trong thư mục `backend/dataset`, với dữ liệu huấn luyện nằm ở `backend/dataset/train` và dữ liệu kiểm định nằm ở `backend/dataset/value`.

4. Huấn luyện mô hình bằng kịch bản huấn luyện đi kèm. Bạn có thể sử dụng bất kỳ mô hình nào trong thư mục `backend/scripts/training`. Ví dụ, để huấn luyện mô hình sử dụng khung EfficientNetV2B0, hãy chạy:

```bash
python scripts/02_train_model_2.ipynb
```

Lưu ý rằng đối với `02_train_dense.ipynb`, bạn cần phải có các tệp `train_landmarks.csv` và `val_landmarks.csv` trong thư mục `backend/dataset`. Các tệp này có thể được tạo ra bằng cách chạy kịch bản `01b_extract_landmarks.py`.

5. Sau khi huấn luyện, mô hình sẽ được lưu trong thư mục `backend/models`. Sau đó, bạn có thể khởi động máy chủ backend:

```bash
uv run backend/app/main.py
```

Bạn có thể thay đổi tệp Keras được sử dụng bằng cách chỉnh sửa biến `MODEL_PATH` trong tệp `backend/app/main.py`.

6. Cuối cùng, khởi động máy chủ frontend:

```bash
cd frontend
npm install
npm run dev
```

Bạn cũng có thể sử dụng `bun` thay cho `npm` nếu đã cài đặt sẵn:

```bash
cd frontend
bun install
bun run dev
```

7. Giao diện frontend hiện tại sẽ chạy tại địa chỉ `http://localhost:5173`. Bạn có thể kiểm tra tính năng nhận diện khuôn mặt bằng cách gửi yêu cầu POST đến backend thông qua việc đưa mặt trước camera trên giao diện frontend. Nếu khuôn mặt được nhận diện, tên của người đó sẽ được hiển thị trên kiosk frontend và cũng sẽ xuất hiện trên serial monitor của ESP32.

## Yêu cầu kỹ thuật (Specifications)

- Mô hình phải được huấn luyện trên bộ dữ liệu khuôn mặt với ít nhất 5 lớp (người) khác nhau.
- Mô hình phải đạt độ chính xác ít nhất 80% trên tập kiểm định (validation set).
- Backend phải có khả năng tiếp nhận yêu cầu POST chứa hình ảnh và trả về lớp dự đoán (tên của người đó) trong ảnh.
- Frontend phải có khả năng hiển thị tên của người được nhận diện khi phát hiện khuôn mặt thông qua camera.
