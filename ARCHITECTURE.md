# Spectrum Matcher — 项目架构文档

## 概述

基于深度学习的 NMR 核磁共振波谱组分鉴定系统。上传 Bruker 格式的 1H-NMR 谱图，AI 模型自动识别其中的植物风味成分。

**技术栈**: FastAPI + TensorFlow/Keras + PySide6 + matplotlib

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│  Client (PySide6 GUI)                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ config.py │  │  api.py  │  │workers.py│  │main_window │  │
│  │ (URL/超时)│  │(HTTP客户端)│  │(QThread) │  │  (PySide6) │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │  HTTP POST (multipart/zip)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Server (FastAPI + uvicorn)                                 │
│  ┌──────────┐  ┌───────────────┐  ┌──────────────────────┐  │
│  │ main.py  │  │ model_runner  │  │     plotter.py       │  │
│  │(路由/解压)│  │ (模型加载/推理) │  │ (matplotlib 绑图)    │  │
│  └──────────┘  └───────┬───────┘  └──────────────────────┘  │
│                        │                                     │
│               ┌────────▼────────┐                            │
│               │   deepmid/      │                            │
│               │  DeepMID_Ori.py │  ← Siamese CNN + SPP      │
│               │  readBruker.py  │  ← Bruker 文件读取         │
│               │  airPLS.py      │  ← 基线校正                │
│               └─────────────────┘                            │
└─────────────────────────────────────────────────────────────┘
```

### 数据流（单次请求）

```
Client                          Server
  │                                │
  │  POST /api/upload              │
  │  zip (Bruker 谱图目录) ──────►  │
  │                                │  1. 解压 zip
  │                                │  2. 扫描 pdata/ 定位谱图目录
  │                                │  3. read_bruker_h_base() 读取 FID
  │                                │  4. airPLS 基线校正
  │                                │  5. predict_DeepMID() 模型推理
  │                                │  6. plot_comparison() 生成 PNG
  │                                │  7. base64 编码 PNG
  │  ◄───────────────────────────  │
  │  JSON: { results,              │
  │          plot_base64,          │
  │          model }               │
  │                                │
  ▼                                │
  解码 base64 → 显示 PNG + 表格
```

**关键设计决策**: 图片以 base64 嵌入 JSON 响应，**单次 HTTP 请求**完成全部传输，无需二次请求 `/api/plot`。

---

## 目录结构

```
spectrum-matcher/
├── client/                          # PySide6 桌面客户端
│   ├── main.py                      #   入口: python main.py
│   └── spectrum_matcher_client/
│       ├── __main__.py              #   包入口
│       ├── app.py                   #   QApplication + DLL路径
│       ├── config.py                #   服务器URL、超时配置
│       ├── api.py                   #   HTTP 客户端 (requests)
│       ├── workers.py               #   QThread workers (Upload, HealthCheck)
│       └── main_window.py           #   主窗口 (390行 PySide6)
├── server/                          # FastAPI 服务端
│   ├── main.py                      #   路由: POST /api/upload
│   ├── model_runner.py              #   模型加载 + 推理 + mock回退
│   ├── plotter.py                   #   matplotlib 谱图绑图
│   ├── model_config.json            #   模型路径和元数据配置
│   ├── Dockerfile                   #   Docker 构建 (备选)
│   └── deepmid/                     #   DeepMID 模型核心代码
│       ├── DeepMID_Ori.py           #     Siamese CNN + SPP 模型定义
│       ├── readBruker.py            #     Bruker NMR 文件读取器
│       └── airPLS.py                #     自适应迭代重加权PLS基线校正
├── tests/                           # 测试用例
│   ├── b1_sample/                   #   B1 配制风味 Bruker 谱图
│   ├── b1_sample.zip                #   预打包测试 zip
│   └── README.md                    #   测试说明
├── docker-compose.yml               # Docker Compose 编排
├── requirements.txt                 # Python 依赖 (参考)
├── ARCHITECTURE.md                  # 本文档
└── .gitignore
```

**注意**: `server/model/` 和 `server/data/` 被 `.gitignore` 排除，包含模型权重和大数据文件。部署时需手动放置。

---

## 核心组件详解

### 1. DeepMID 模型 (`server/deepmid/DeepMID_Ori.py`, 294行)

**架构**: Siamese CNN + Spatial Pyramid Pooling

```
输入 R (32724点)              输入 S (32724点)
      │                              │
Conv1D(32,5) + ReLU             Conv1D(32,5) + ReLU
MaxPool1D(2)                    MaxPool1D(2)
8× [Conv1D(32,5)+ReLU           8× [Conv1D(32,5)+ReLU
    +MaxPool1D(2)]                   +MaxPool1D(2)]
      │                              │
      └────── concatenate ──────────┘
                  │
           Reshape(59,64,1)
           Conv2D(128, 5×5, stride=2) + ReLU
                  │
      Spatial Pyramid Pooling [1,2,3,4]
                  │
           Dense(100) + ReLU + Dropout(0.2)
                  │
           Dense(1) + Sigmoid
                  │
           输出: 概率 0~1
```

- **参数量**: 470,345 (1.79 MB)
- **输入**: 两个 1D NMR 谱 (各 32724 点)，R=参考物，S=待测物
- **输出**: R 是 S 的成分 → 1，R 不是 S 的成分 → 0
- **训练**: 离线预计算增强数据 (.pkl)，正样本=同植物不同处理，负样本=不同植物
- **Keras 3 兼容**: `tf.expand_dims` → `layers.Reshape`, `get_shape()` → `.shape`, `load_model(safe_mode=False)`

### 2. Bruker 读取器 (`server/deepmid/readBruker.py`, 73行)

读取 Bruker TopSpin 格式的 1H-NMR 数据:
- 路径: `{sample_dir}/1/pdata/1/` → 读取 `1r` (实部) 和 `proc` 参数
- 计算 ppm 化学位移轴: SW, O1, BF1 → start/end/step
- airPLS 基线校正 (λ=100, porder=1, 15次迭代)
- 溶剂峰归零 (水峰 4.7ppm, DMSO 2.5ppm 等区域)
- MinMax 归一化到 [0, 1]
- 裁剪到 10.7~0.3 ppm (32724 数据点)

### 3. 模型运行器 (`server/model_runner.py`, 170行)

```
init()                              match(query_dir)
  │                                     │
  ├─ 读取 model_config.json             ├─ 读取 Bruker 谱图
  ├─ 检查模型文件 (.h5)                  ├─ 与全部参考谱比对
  ├─ 检查参考数据 (plant_flavors)        │   R[i]=ref[i].fid
  ├─ load_DeepMID() 加载模型             │   Q[i]=query.fid
  ├─ read_bruker_hs_base() 加载参考库    ├─ predict_DeepMID(model, [R,Q])
  └─ 若缺失 → mock 模式                 └─ 按概率排序返回
```

**Mock 模式**: 模型或数据缺失时自动回退，生成合成谱图和模拟概率，保证 API 可测试。

### 4. 谱图绑图 (`server/plotter.py`, 67行)

- matplotlib Agg 后端 (无需 GUI)
- 生成 2800×1200 像素 PNG (14"×6" @ 200 DPI)
- 黑色查询谱 + 彩色 top-N 参考谱叠加
- X 轴反转 (高场→低场, NMR 惯例)
- 灰色半透明填充增强可读性

### 5. 客户端主窗口 (`client/spectrum_matcher_client/main_window.py`, 382行)

**UI 布局**:
```
┌─────────────────────────────────────────┐
│ Server: [https://nmr.ooney.xyz] [Test]  │  ← 服务器配置行
├─────────────────────────────────────────┤
│    Drag & drop Bruker folder or .zip    │  ← 拖拽区
│          here, or click to browse       │
├─────────────────────────────────────────┤
│ [███████████████        ] Elapsed: 5.2s │  ← 进度条 + 计时
│ [Select Folder] [Select .zip]           │  ← 按钮行
├─────────────────────────────────────────┤
│ Flavor Name              │ Probability  │  ← 结果表格
│ Roman Chamomile Ext-A    │    0.9903    │
│ Fig Extraction           │    0.9240    │
│ ...                                   │
│ Model: DeepMID | Siamese CNN+SPP | 470K│  ← 模型信息
├─────────────────────────────────────────┤
│                                         │  ← 对比谱图
│         [NMR Comparison Plot]           │
│                                         │
└─────────────────────────────────────────┘
```

**功能**:
- 服务器 URL 可编辑 + 连接测试 (实时状态指示)
- 拖拽文件夹或 .zip 文件
- 上传计时 (Elapsed / Done in Xs)
- 模型信息展示 (name / arch / params)
- base64 内联图片渲染 (无需额外请求)
- closeEvent 线程安全清理 (cancel + quit + wait)
- Worker 异常全捕获 (traceback.print_exc + UI 错误提示)

### 6. Worker 线程 (`client/spectrum_matcher_client/workers.py`)

| Worker | 父类 | 功能 |
|--------|------|------|
| `UploadWorker` | QThread | 打包文件夹→zip → HTTP POST → 返回结果 |
| `HealthCheckWorker` | QThread | GET /docs → 连通性检测 |

**线程安全设计**:
- `_is_cancelled` 标志 → 支持中途取消
- 信号 (`finished` / `error`) → Qt 事件队列跨线程通信
- `deleteLater()` → 安全释放
- closeEvent 中 `cancel()` + `quit()` + `wait(3000)`

---

## API 接口

### POST /api/upload

**请求**: `multipart/form-data`, 字段 `file` = Bruker 谱图目录的 .zip 压缩包

**响应**:
```json
{
    "query_name": "B1",
    "results": [
        {"name": "Roman Chamomile Extraction-A", "probability": 0.9903},
        {"name": "Fig Extraction",               "probability": 0.9240}
    ],
    "plot_base64": "iVBORw0KGgo... (255KB)",
    "model": {
        "name":   "DeepMID",
        "arch":   "Siamese CNN + Spatial Pyramid Pooling",
        "params": "470K",
        "task":   "NMR mixture component identification"
    }
}
```

---

## 配置系统

### 模型配置 (`server/model_config.json`)

```json
{
    "model_path": "model/model_1/test_nmr",
    "data_path":  "data/plant_flavors",
    "name":       "DeepMID",
    "arch":       "Siamese CNN + Spatial Pyramid Pooling",
    "params":     "470K",
    "task":       "NMR mixture component identification"
}
```

### 环境变量覆盖

| 变量 | 作用 | 示例 |
|------|------|------|
| `SPECTRUM_MATCHER_MODEL` | 模型文件路径 | `model/model_1/tea.h5` |
| `SPECTRUM_MATCHER_DATA` | 参考谱图目录 | `data/tea_samples` |
| `SPECTRUM_MATCHER_SERVER_URL` | 客户端默认服务器 | `http://192.168.3.6:8000` |
| `SPECTRUM_MATCHER_TIMEOUT` | 请求超时(秒) | `120` |

### 客户端配置 (`client/.../config.py`)

```python
DEFAULT_SERVER_URL      = "https://nmr.ooney.xyz"
LOCAL_SERVER_URL        = "http://192.168.3.6:8000"
DEFAULT_TIMEOUT_SECONDS = 120
```

---

## 部署

### 生产环境 (systemd 自启动)

```bash
# 服务文件: /etc/systemd/system/nmr-matcher.service
sudo systemctl status nmr-matcher
sudo systemctl restart nmr-matcher
journalctl -u nmr-matcher -f
```

服务配置:
- **用户**: zhao (非 root)
- **工作目录**: /home/zhao/spectrum-matcher/server
- **Python venv**: /home/zhao/spectrum-matcher/DeepMID-main/.venv
- **端口**: 8000
- **重启策略**: 异常退出 5 秒后自动重启
- **开机启动**: `WantedBy=multi-user.target`

### 公网访问

通过 Cloudflare Tunnel 暴露到 `https://nmr.ooney.xyz`:
```bash
cloudflared tunnel run nmr-matcher
```

### 本地开发

```bash
# 服务端
cd server
source ../DeepMID-main/.venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# 客户端
cd client
pip install PySide6 requests
python main.py
```

---

## 依赖

### 服务端 (venv + TF 2.21.0 + GPU)

```
tensorflow==2.21.0           # 深度学习框架 (Keras 3)
nvidia-cudnn-cu12==9.22      # GPU 加速
nvidia-cublas-cu12==12.9     # GPU 线性代数
nvidia-cuda-runtime-cu12     # CUDA 运行时
fastapi==0.136               # Web 框架
uvicorn==0.48                # ASGI 服务器
matplotlib==3.10             # 谱图绑图
nmrglue==0.11                # NMR 文件解析
numpy==2.2                   # 数值计算
scipy==1.15                  # 科学计算
scikit-learn==1.7            # 机器学习工具
pandas==2.3                  # 数据处理
```

### 客户端 (仅 PySide6 + requests)

```
PySide6==6.11                # Qt GUI 框架
requests==2.34               # HTTP 客户端
```

---

## 模型训练流程 (参考)

1. **数据准备**: 13 种植物提取物 Bruker 谱图 → `data/plant_flavors/`
2. **数据增强**: `augment.py` 生成正/负样本对 → `aug/*.pkl`
3. **模型训练**: `DeepMID_Ori.py` (bTrain=True) → 20 epochs → val_acc ~85%
4. **模型部署**: 复制 `.h5` + `.pkl` 到 `server/model/model_1/`
5. **配置**: 更新 `model_config.json` 中的 `model_path`

---

## 硬件要求

| 组件 | 最低 | 推荐 |
|------|------|------|
| CPU | 4 核 | 8 核 |
| RAM | 8 GB | 16 GB |
| GPU (训练) | 无 (CPU可用) | NVIDIA 8GB+ VRAM |
| GPU (推理) | 无 (CPU ~100ms) | NVIDIA 4GB+ |
| 磁盘 | 2 GB | 5 GB (含训练数据) |

当前生产环境: AMD Ryzen 7 7840H + RTX 4060 8GB + 16GB RAM + Ubuntu 22.04

---

## 版本历史

| 版本 | 日期 | 关键变更 |
|------|------|----------|
| v1.0 | 2026-05-21 | 初始框架: FastAPI server + PySide6 client + mock mode |
| v1.1 | 2026-05-27 | Keras 3 兼容修复, Docker 部署 |
| v1.2 | 2026-05-28 | 模型部署, 客户端优化 (server URL、zip拖拽、健康检查) |
| v1.3 | 2026-05-28 | 线程安全修复, zip 目录解析修复 |
| v1.4 | 2026-05-28 | 计时器、高DPI绑图、模型信息展示 |
| v1.5 | 2026-05-28 | base64内联图表、移除/plot接口、单请求架构 |
| v1.6 | 2026-05-28 | model_config.json 配置化、systemd 开机自启 |
