# Final Project - Home Greeting System with Face Recognition

[English](README.md) | [中文](README.cn.md) | [Français](README.fr.md)

## 项目简介

这是一个问候系统，通过 TensorFlow 和 Keras 训练模型来识别人脸。随后会使用 ESP32 控制器调用 Python 后端，在前端信息屏上显示识别到的人名。

## 技术栈

- Python
- TensorFlow
- Keras
- ESP32
- FastAPI（后端）
- React（Vite）（前端）

## 运行方式

1. 首先，克隆仓库并进入后端目录：

```bash
git clone
```

2. 安装后端所需依赖：

```bash
cd backend
pip install -r requirements.txt
```

你也可以选择使用 `uv` 包管理器来安装依赖：

```bash
uv sync
```

3. 按照提示运行以下命令来采集数据集：

```bash
python backend/scripts/01a_collect_faces.py
```

采集到的数据会存放在 `backend/dataset` 目录中，其中训练数据位于 `backend/dataset/train`，验证数据位于 `backend/dataset/value`。

4. 使用提供的训练脚本训练模型。你可以使用 `backend/scripts/training` 目录中的任意模型。例如，要使用 EfficientNetV2B0 作为骨干网络训练模型，请运行：

```bash
python scripts/02_train_model_2.ipynb
```

请注意，对于 `02_train_dense.ipynb`，你需要在 `backend/dataset` 目录中准备好 `train_landmarks.csv` 和 `val_landmarks.csv` 文件，这些文件可以通过运行 `01b_extract_landmarks.py` 脚本生成。对于 `02_train_model_1.ipynb` 和 `02_train_model_2.ipynb`，则不需要生成这些 landmark CSV 文件，因此如果你打算使用这两个脚本训练，可以跳过 `01b_extract_landmarks.py`。

5. 训练完成后，模型会保存在 `backend/models` 目录中。随后你可以使用 uvicorn 启动后端服务：

```bash
uvicorn main:app --reload
```

你可以通过修改 `backend/app/main.py` 中的 `MODEL_PATH` 变量，来更换所使用的 keras 文件（即训练脚本生成的模型）。

6. 最后，启动前端服务：

```bash
cd frontend
npm install
npm run dev
```

如果你已经安装了 `bun`，也可以使用它代替 `npm`：

```bash
cd frontend
bun install
bun run dev
```

7. 此时前端应该已经运行在 `http://localhost:5173`。你可以通过前端界面让摄像头看到你的脸，并向后端发送 POST 请求来测试人脸识别。如果识别成功，页面上会显示该人的姓名，同时 ESP32 的串口监视器中也会显示该姓名。

## ESP32 配置（后端联调）

本项目包含位于 `backend/esp32/` 的 ESP32 固件，用于轮询后端接口（如 `/api/kiosk-status` 和 `/api/health`）。

### 1. 安装 Arduino IDE

- 从官网下载安装 Arduino IDE：https://www.arduino.cc/en/software

### 2. 在 Arduino IDE 中配置 ESP32

1. 打开 Arduino IDE。
2. 进入 `File > Preferences`。
3. 在 `Additional boards manager URLs` 中添加：

```text
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

4. 进入 `Tools > Board > Boards Manager`。
5. 搜索 `esp32`，安装 `esp32 by Espressif Systems`。
6. 使用 USB-C 连接开发板。
7. 在 `Tools > Board` 中选择 `ESP32 Dev Module`。
8. 在 `Tools > Port` 中选择对应的 COM 端口。

如果上传失败，请确认 USB 线支持数据传输（不是仅充电），并检查板型和端口是否选择正确。

### 3. 硬件清单

- 2x LED
- 1x ESP32 WROOM 30 pin ism2.4c 302 USB-C
- 1x 16x2 I2C LCD（带背板，5V）
- 1x 超声波传感器 HC-SR04（5V）
- 1x USB-C 转 USB-A 适配器（按你的 ESP32 接口决定）

### 4. 重要电气说明（分压）

ESP32 GPIO 逻辑电平为 3.3V，HC-SR04 Echo 引脚可能输出 5V。

请在 `HC-SR04 Echo` 与 ESP32 Echo 输入引脚之间使用分压电路，将信号降至约 3.3V。不要把 Echo 直接接到 ESP32 GPIO。

### 5. 固件与接口配置

1. 在 Arduino IDE 中打开 `backend/esp32/kiosk_status_serial.ino`。
2. 配置：
	- `WIFI_SSID`
	- `WIFI_PASS`
	- `API_BASE_URL`（填写你电脑的局域网 IP 和后端端口，例如 `http://192.168.100.94:3009`）
3. 上传到 ESP32。
4. 串口监视器波特率设置为 `115200`。

### 6. 板子引脚参考图

![ESP32 引脚参考图](frontend/public/boardpinout.png)

## 规范

- 模型应使用人脸数据集进行训练，并至少包含 5 个不同类别（人物）。
- 模型在验证集上的准确率应至少达到 80%。
- 后端应能够接收带有图片的 POST 请求，并返回图片中预测的类别（人物姓名）。
- 前端应能够在通过摄像头检测到人脸时显示识别到的姓名。
