# 开发日志

## 2026-05-20 — 项目初始化

- 创建项目脚手架：FastAPI 服务端 + PySide6 客户端 + DeepMID 模型接口桩代码。

## 2026-05-21 — 客户端原型 + 服务端 Mock 模式

- 重构客户端为 Python 包 `client/spectrum_matcher_client/`，含 `config.py`、`api.py`、`workers.py`、`main_window.py`。
- 添加标准库 Mock 服务器 `client/tools/mock_server.py`，支持 `POST /api/upload` 和 `GET /api/plot/mock-plot`，返回 3 个合成风味结果和程序化生成的 PNG 对比图。
- 验证客户端包导入、模拟上传、绘图下载全链路通过。
- 修复 Windows 下 `DLL load failed` 问题：在导入 Qt 前将 PySide6/shiboken6 目录加入 DLL 搜索路径。
- 服务端实现 Mock 模式：`model_runner.py` 自动检测模型文件可用性，缺失时回退到合成 NMR 谱图数据。
- 服务端实现 `plotter.py`：使用 matplotlib Agg 后端生成查询谱图与 Top-N 参考谱图叠加的对比 PNG。
- Docker 支持：`tensorflow/tensorflow:2.5.0` 镜像 + 阿里云 PyPI 镜像；`docker-compose.yml` 挂载模型/数据卷。
- 配置 Cloudflare Tunnel，将 `nmr.ooney.xyz` 路由到 `localhost:8000`，systemd 服务 `cloudflared-nmr` 实现开机自启。
- 客户端默认服务器地址设为 `https://nmr.ooney.xyz`。
- 编写客户端端到端测试指南 `TESTING.md`。

## 2026-05-28 — 模型集成与客户端增强

- **Keras 3 兼容性修复**：TF 2.21 环境下，`tf.expand_dims` 替换为 `Reshape` 层，`get_shape()` 改为 `.shape`，`load_model` 添加 `safe_mode=False`，修复 `airPLS` 导入路径。
- **客户端功能增强**：
  - 服务器 URL 可编辑输入框 + 连接测试按钮。
  - 拖拽上传支持文件夹和 `.zip` 文件，自动检测 `pdata/` 子目录验证 Bruker 谱图结构。
  - `HealthCheckWorker` 异步检测服务器连通性，状态实时显示。
  - 上传完成后显示 Top 匹配结果名称和概率。
- **B1 测试用例**：添加 B1 配方风味的真实 Bruker 1H-NMR 谱图（MeOD 溶剂，600 MHz，128 scans）作为测试数据。
- **Worker 异常全捕获**：防止上传/绘图线程异常崩溃，增加 `cancel()` 方法支持优雅关闭，`closeEvent` 中安全停止运行中的线程。
- **pdata/ 目录扫描修复**：兼容扁平结构和带外层目录的 zip 结构。
- **请求超时调整**：默认超时增至 120 秒，适应 Cloudflare Tunnel 延迟。

## 2026-05-28 — 架构升级 v1.5/v1.6

- **单请求架构（v1.5）**：
  - 图表以 base64 编码内联到 JSON 响应中，移除 `GET /api/plot/{id}` 端点和客户端 `PlotWorker`。
  - 一次 HTTP 请求完成全部传输，无需二次调用。
- **图表质量提升**：DPI 120→200，尺寸 12×5→14×6 英寸，字体加大，网格透明度优化。
- **上传计时器**：客户端增加基于 `QTimer` 的耗时显示，上传中显示 "Elapsed: X.Xs"，完成后显示 "Done in X.Xs"。
- **模型信息展示**：API 返回模型名称、架构、参数量，客户端在结果表格下方显示模型归属面板。
- **模型配置化（v1.6）**：
  - 新增 `server/model_config.json`，支持模型路径、参考数据路径和元数据配置。
  - 环境变量 `SPECTRUM_MATCHER_MODEL` / `SPECTRUM_MATCHER_DATA` 覆盖配置文件。
  - Dockerfile 升级到 TF 2.21 + NVIDIA GPU 支持。
- **项目架构文档**：编写 `ARCHITECTURE.md`，详细记录系统架构、数据流、目录结构、核心组件、API 接口、部署方案。

## 2026-05-30 — 富客户端与延迟优化

- **GZip 压缩**：服务端添加 `GZipMiddleware`，响应体积减小约 39%（~1MB → ~625KB），Cloudflare Tunnel 传输时间从 ~24.6s 降至 ~20s。
- **降采样工具**：新增 `server/downsample.py`，32,724 点 → ~3,000 点均匀降采样（91% 缩减），降采样后的谱图数据随响应发送到客户端。
- **客户端交互式绑图**：
  - 新增 `plot_widget.py`：基于 matplotlib `FigureCanvasQTAgg` + `NavigationToolbar2QT`，支持缩放、平移、保存。
  - 替换静态 QLabel 绑图显示，降采样数据可用时优先渲染交互式图表，否则回退到 base64 PNG。
- **菜单栏与快捷键**：
  - 文件菜单：打开文件夹 (Ctrl+O)、打开 Zip (Ctrl+Shift+O)、导出 CSV (Ctrl+E)、导出 JSON (Ctrl+Shift+E)、导出 PNG (Ctrl+P)、退出 (Ctrl+Q)。
  - 视图菜单：绑图工具栏开关。
  - 帮助菜单：关于对话框。
- **QSettings 持久化**：新增 `settings.py`，保存服务器 URL、窗口位置/大小、最近浏览目录、工具栏可见性。
- **结果导出**：新增 `export.py`，支持 CSV（名称+概率）、JSON（完整数据）、PNG（高分辨率绑图）。
- **可排序结果表格**：添加序号列，概率列支持数值排序（非字母序），表头点击排序。
- **上传进度条**：`ProgressReader` 包装文件对象回传进度，`UploadWorker` 新增 `progress` 信号，进度条从不确定模式切换为确定模式。
- **真正的取消机制**：API 层使用 `threading.Event` + `stream=True` + `iter_content` 实现分块检查取消，`cancel()` 可中断进行中的 HTTP 请求。
- **结果历史**：内存中保留最近 20 次上传结果，通过下拉框按时间戳和查询名称切换历史记录。
- **QStatusBar**：替代内联状态标签，显示连接状态、上传进度、Top 匹配结果、错误信息。
- **工具提示**：所有主要控件添加悬停提示。
- **Mock 服务器更新**：返回 13 个植物风味（含降采样数据、base64 绑图、模型信息），移除 `/api/plot` 端点。

## 2026-05-30 — 测试体系与 EXE 打包

- **Pytest 测试套件（33 个测试）**：
  - `test_downsample.py`（9）：步进取样算法的各种输入类型和边界条件。
  - `test_api.py`（15）：HTTP 客户端与 Mock 服务器集成，响应格式验证，取消机制。
  - `test_export.py`（8）：CSV/JSON/PNG 导出功能，Unicode 支持。
  - `conftest.py`：共享 fixtures（Mock 服务器、临时目录、API 客户端）。
- **6 个演示用 Bruker 谱图 zip**：不同溶剂（MeOD、DMSO、CDCl3）、频率（400/500/600 MHz）、扫描次数（16-512），体积 172-489 KB，用于 UI 功能展示。
  - `generate_demo_zips.py`：可重新生成更多变体。
- **Windows EXE 打包**：
  - `client/spectrum-matcher.spec`：PyInstaller 配置文件。
  - `.github/workflows/build-exe.yml`：推送 `v*` 标签自动构建 EXE + 创建 Release。
  - v0.1.0 发布：`NMR-Spectrum-Matcher-win64.zip` 含 PySide6 + matplotlib + requests 全部依赖。
- **README 更新**：添加下载说明、架构图、Mock 服务器使用、配置表格。

## 2026-05-31 — 错误处理与工业级测试

- **服务端错误处理修复**：
  - `main.py`：上传处理逻辑包裹 try/except，异常返回 HTTP 500 + 清晰错误信息；临时文件清理使用 `ignore_errors=True`。
  - `model_runner.py`：真实模式前检查 `1/pdata/1/` 目录存在性，避免 `FileNotFoundError` 崩溃。
- **QThread 竞态条件修复**：
  - `workers.py`：信号发射移到 `finally` 块之后，确保线程完全结束后再通知主线程。
  - `main_window.py`：新上传前断开旧 Worker 信号，防止陈旧信号干扰；使用 `QThread.finished` 安全清理。
- **工业级测试套件（101 个新测试，96 通过 0 失败）**：
  - `tests/server/`（34 测试）：TestClient 端点测试、模型运行器（Mock 模式）、绑图生成、airPLS 基线校正。
  - `tests/client/`（14 测试）：URL/超时配置、QSettings 持久化、线程生命周期与信号、交互式绑图组件。
  - `tests/integration/`（10 测试）：E2E 管线（Mock 服务器）、错误处理（连接拒绝/超时/服务端错误）、生产环境（可选）。
  - `tests/edge_cases/`（12 测试）：损坏的 zip、非 Bruker zip、空 zip、缺少 pdata/、并发上传、取消操作。
  - `tests/fixtures/`（4 个）：空 zip、损坏字节 zip、非 Bruker 合法 zip、无 pdata/ 的 Bruker 风格 zip。
  - `.github/workflows/tests.yml`：CI 矩阵（Python 3.10/3.11/3.12），覆盖率报告。
