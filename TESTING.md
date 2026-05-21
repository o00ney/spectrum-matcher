# 端到端测试指南

## 前置条件

- Python 3.8+
- `pip install PySide6 requests`

## 测试方式一：连接线上服务（推荐）

服务端已在 `https://nmr.ooney.xyz` 运行（mock 模式），直接启动客户端即可：

```bash
git clone https://github.com/o00ney/spectrum-matcher.git
cd spectrum-matcher/client
pip install PySide6 requests
python -m spectrum_matcher_client
```

**操作步骤**：
1. 启动后会看到窗口，顶部显示 `Server: https://nmr.ooney.xyz`
2. 点击 "Select Folder" 或拖入任意文件夹
3. 客户端自动打包上传，几秒后显示匹配结果表格 + 谱图对比图

> mock 模式下不需要真实的 Bruker 谱图文件，任意文件夹即可

## 测试方式二：本地 mock 服务器

无需网络，纯本地验证客户端：

```bash
# 终端 1：启动 mock 服务器
cd spectrum-matcher/client/tools
python mock_server.py
# 输出: Mock server running at http://127.0.0.1:8000

# 终端 2：启动客户端（默认连 127.0.0.1:8000）
cd spectrum-matcher/client
python -m spectrum_matcher_client
```

## 预期结果

| 步骤 | 预期 |
|------|------|
| 启动客户端 | 窗口标题 "NMR Spectrum Matcher"，显示拖放区域 |
| 选择文件夹 | 进度条出现，按钮禁用 |
| 上传完成 | 表格显示 13 个植物风味，按概率降序排列 |
| 图片加载 | 下方显示 NMR 谱图对比图（查询 + Top 3 参考） |

## 切换服务器地址

```bash
# 方式 A：环境变量
export SPECTRUM_MATCHER_SERVER_URL=https://nmr.ooney.xyz

# 方式 B：修改 client/spectrum_matcher_client/config.py 中的 DEFAULT_SERVER_URL
```
