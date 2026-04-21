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

## 规范

- 模型应使用人脸数据集进行训练，并至少包含 5 个不同类别（人物）。
- 模型在验证集上的准确率应至少达到 80%。
- 后端应能够接收带有图片的 POST 请求，并返回图片中预测的类别（人物姓名）。
- 前端应能够在通过摄像头检测到人脸时显示识别到的姓名。
