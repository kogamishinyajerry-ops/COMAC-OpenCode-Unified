# ollama-models/ — GGUF Model Storage

> 部署机本地推理所需的 GGUF 模型文件存放在此目录。
> `.gitignore` 已排除此目录内容(模型太大, 不入 Git)。

---

## 当前推荐: qwen2.5-1.5b-instruct-q4_K_M

| 项 | 值 |
|---|---|
| 文件名 | `qwen2.5-1.5b-instruct-q4_k_m.gguf` |
| 大小 | ~1.0 GB |
| 量化 | Q4_K_M (4-bit, 主流甜点) |
| 适用 | vGPU 1GB / 16GB RAM / CPU 推理 |
| 速度 (估) | 10-18 tok/s on 8-core CPU |
| 中文 | 优秀 (Qwen 系列强项) |
| 工具调用 | 良好 (OpenCode 场景够用) |

---

## 备选模型 (按优先级排序)

### 1. qwen2.5-1.5b-instruct-q4_K_M ⭐ (推荐)

- Hugging Face: https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF
- 选 `qwen2.5-1.5b-instruct-q4_k_m.gguf`
- 在 `providers.json` 用 `qwen-fast` 块 (默认 disabled)

### 2. qwen3-4b-instruct-q4_K_M (默认)

- Hugging Face: https://huggingface.co/Qwen/Qwen3-4B-Instruct-GGUF
- 选 `qwen3-4b-instruct-q4_k_m.gguf`
- 在 `providers.json` 用 `llamacpp` 块 (默认 enabled)
- vGPU 1GB 必须 CPU 跑, 速度 3-6 tok/s

### 3. qwen2.5-3b-instruct-q4_K_M (平衡)

- Hugging Face: https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF
- 选 `qwen2.5-3b-instruct-q4_k_m.gguf`
- 1.8 GB, 速度介于 1.5B 和 4B 之间
- 需要自己改 `llamacpp` 块的 `modelPath`

### 4. llama-3.2-1b-instruct-q4_K_M (英文强)

- Hugging Face: https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct-GGUF
- 0.8 GB, 比 Qwen 1.5B 还小
- 英文好, 中文一般

### 5. qwen2.5-0.5b-instruct-q4_K_M (极速)

- Hugging Face: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
- 0.5 GB
- 速度 20-35 tok/s
- OpenCode 工具调用错误率 ~50%, 不推荐

---

## 镜像源 (内网/网络受限)

| 源 | 用途 |
|---|---|
| Hugging Face | 主源, 国外 |
| ModelScope (魔搭) | 国内镜像: https://www.modelscope.cn/ |
| Ollama (本地化) | `ollama pull qwen2.5:1.5b` 然后从 `~/.ollama/models/` 找 .gguf |
| HF-Mirror | 国内代理: https://hf-mirror.com/ |

---

## 下载命令 (PowerShell)

```powershell
# 1. 创建目录
New-Item -ItemType Directory -Force -Path "ollama-models"

# 2. 下载 (选一个)
# Hugging Face
Invoke-WebRequest -Uri "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf" -OutFile "ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf"

# HF-Mirror (国内)
Invoke-WebRequest -Uri "https://hf-mirror.com/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf" -OutFile "ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf"

# 3. 验证
Get-FileHash "ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf" -Algorithm SHA256
# 对比 Hugging Face 页面上的 sha256
```

## 下载命令 (CMD / curl)

```cmd
:: 创建目录
mkdir ollama-models

:: 下载 (curl)
curl -L -o ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf ^
  "https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"

:: 验证
certutil -hashfile ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf SHA256
```

---

## 启用 qwen-fast (1.5B) 流程

1. **下载** `qwen2.5-1.5b-instruct-q4_k_m.gguf` 到此目录
2. **验证** sha256 与 HF 页面一致
3. **编辑** `providers.json`:
   ```json
   {
     "id": "qwen-fast",
     ...
     "enabled": false    <-- 改为 true
   }
   ```
4. **运行** `start-qwen.bat` (会自动启动 2 个本地 provider, 端口 11435 和 11436)
5. **验证** 浏览器开 `http://127.0.0.1:11436/v1/models`

## 切换模型(从 4B 切到 1.5B)

| 步骤 | 操作 |
|---|---|
| 1 | 关 4B: `stop-qwen.bat` |
| 2 | 启用 1.5B: 编辑 `providers.json` 把 `qwen-fast.enabled: false → true` |
| 3 | 可选: 关 4B: `llamacpp.enabled: true → false` (减少菜单噪声) |
| 4 | 重启: `start-qwen.bat` |
| 5 | `run.bat` 选 1.5B |

## 同时跑 4B + 1.5B

- `llamacpp` 占端口 11435
- `qwen-fast` 占端口 11436
- `probe.py` 同时管理两个, watchdog 监控两个
- `run.bat` 菜单显示两个, 用户自选

---

## 模型删除 (回收磁盘)

```cmd
:: 查看占用
dir ollama-models\*.gguf

:: 删除 4B (留 1.5B)
del ollama-models\qwen3-4b-q4_k_m.gguf

:: 删除 1.5B (留 4B)
del ollama-models\qwen2.5-1.5b-instruct-q4_k_m.gguf
```

---

## 验证文件完整性 (sha256)

| 模型 | sha256 (示例, 以 HF 页面为准) |
|---|---|
| qwen2.5-1.5b-instruct-q4_k_m.gguf | 见 HF model card |
| qwen3-4b-instruct-q4_k_m.gguf | 见 HF model card |

⚠️ 实际 sha256 请去 Hugging Face 模型的 "Files and versions" 页面查, 不要用本文件示例值。
