# DEPLOY-VGPU.md — vGPU / Low-VRAM Deployment Guide

> 适用: NVIDIA vGPU profiles (M10 / M60 / RTX6000-1Q/2Q/4Q/8Q), 16 GB 系统 RAM, Windows 10 VDI
> 不适用: 物理 RTX 3060+ 用户 (请把 `ngl` 调到 14+)

---

## 1. 你的部署画像 (How to read this doc)

打开 `任务管理器 → 性能 → GPU`,看"专用 GPU 内存"那一行:

| 专用 GPU 内存 | 你的画像 | 推荐配置 |
|---|---|---|
| 0.5-1.0 GB | **vGPU 1Q / 1B** (VDI, 笔记本) | ngl=0, 1.5-3B 模型 |
| 1.0-2.0 GB | vGPU 2Q / 老独显 | ngl=0, 1.5-3B 模型 |
| 2.0-4.0 GB | vGPU 4Q / GTX 1650 | ngl=20, 1.5-4B 模型 |
| 4.0-8.0 GB | vGPU 8Q / RTX 3060 Laptop | ngl=99, 4-7B 模型 |
| 8.0+ GB | 物理 RTX 3060+ (8 GB+) | ngl=99, 7-14B 模型 |

⚠️ **"共享 GPU 内存"不算** — vGPU 驱动不允许计算负载用共享内存(只用于显示)。

---

## 2. v2.3.5 锁死两个 provider

v2.3.5 决定:**只支持 GLM-5.1-AWQ-4bit (内网) + Qwen2.5-Coder-3B (本地)** 两个 provider。

之前 v2.2.1 引入的 `qwen-fast` 1.5B fallback **已删除**:
- 1.5B 实际 tok/s 在部署机 (2018 款 4-8 核 CPU) 跑 8-12,跟 3B 拉不开差距
- 1.5B 工具调用成功率明显低(实测 70% vs 3B 85%)
- 多一个 provider 多一份维护成本 (路径、端口、healthcheck、菜单)
- **少就是多**

---

## 3. 核心约束:qwen3-4b 装不进 1 GB vGPU

| 资源 | 占用 |
|---|---|
| qwen3-4b q4_K_M 模型 | **2.5 GB** 显存 |
| qwen3-4b q8_0 | 4.5 GB |
| 你的 vGPU 1Q 专用显存 | **1.0 GB** |
| **结论** | **❌ 装不下, 必须 CPU 跑** |

ngl (number of GPU layers) 是关键参数。ngl=99 = 全 GPU 卸载, ngl=0 = 全 CPU。

**vGPU 1Q 唯一可行值:ngl=0** (CPU 推理, 用 16 GB 系统 RAM 装模型)

---

## 4. 两种加速方案 (任选一种)

### 方案 A:内网 New API (快, 不动本地模型) ⭐ 优先

如果内网 New API 可用 (10.136.232.50:80):

1. 编辑 `providers.json`:
   ```json
   "newapi" 块:
       "enabled": false  →  true
       "apiKey": "YOUR_NEWAPI_KEY_HERE"  →  真实 key
       "baseURL":  →  确认可连通的内网地址
   ```
2. 跑 `python probe.py` 刷新 `_runtime.bat`
3. `run.bat` 跑起来,主菜单应显示 `GLM-5.1-AWQ-4bit` 亮起
4. 这是内网 GPU 服务器,速度 ~30-50 tok/s, 不消耗本机资源

### 方案 B:本地 Qwen2.5-Coder-3B (CPU 跑, 已默认启用)

1. 下载 `qwen2.5-coder-3b-instruct-q4_k_m.gguf` (~1.9 GB)
   - Hugging Face: https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF
   - 文件名: `qwen2.5-coder-3b-instruct-q4_k_m.gguf`
2. 拷到 `ollama-models\qwen2.5-coder-3b-instruct-q4_k_m.gguf`
3. `start-qwen.bat` 启 llama-server 11435 端口
4. `run.bat` 选 `[1] Qwen` (或 [2] GLM 如果启用了 newapi)
5. CPU 跑 8-10 tok/s, agent 循环 5 步 2-3 分钟

### 方案 C (备选):找 IT 要更大的 vGPU profile

- 当前: vGPU 1Q = 1 GB
- 申请: vGPU 4Q = 4 GB 或 8Q = 8 GB
- 改 `providers.json` 的 `startupArgs.ngl` 从 0 → 14
- 4 GB profile 可跑 qwen3-4b GPU 加速 (~25-40 tok/s)
- 走流程可能要 1-2 周

---

## 5. 验证步骤 (10 步定位"卡"vs"崩")

```cmd
:: 1. 拉最新代码
cd COMAC-OpenCode-Unified
git pull origin main

:: 2. 确认 commit hash
git log --oneline -1
:: 期望: 看到 "v2.3.5" 或更新的 commit

:: 3. 跑诊断
doctor.bat
:: 期望: GPU 0% (正常, 没在跑), Python 绿, 端口绿

:: 4. 单独起 llama-server
start-qwen.bat
:: 期望看到: "model loaded" + "llama server listening on 127.0.0.1:11435"

:: 5. 浏览器测连通
start http://127.0.0.1:11435/v1/models
:: 期望: JSON 列出 "qwen2.5-coder-3b-instruct-q4_K_M"

:: 6. 测 opencode.json 配置
type opencode.json
:: 期望: baseURL = http://127.0.0.1:11435/v1

:: 7. 真测 OpenCode
run.bat
:: 选 [1] Qwen (本地) 或 [2] GLM (远程, 如果启用了 newapi)

:: 8. 输入"你好"看回不回
> 你好
:: 期望: 1-3 秒后出回复

:: 9. 测延迟
> 用 Python 写一个 hello world
:: 期望: 10-30 秒生成完毕 (本地 CPU) 或 3-8 秒 (内网 GLM)

:: 10. 跑 benchmark 建基线
benchmark.bat
:: 期望: 看到 5 轮 tok/s 数据, 记下来给后续对比
```

把 10 步的实际输出贴给我,我能立刻知道是崩还是慢,以及为什么。

---

## 6. 常见故障对照表

| 现象 | 原因 | 修法 |
|---|---|---|
| 启动后 1 秒就崩 | 模型文件不存在 / 路径错 | 检查 `ollama-models\` 有 .gguf 文件 |
| 启动后 30 秒 OOM | RAM 不够 | 改 `context=4096`, `threads=4` |
| 启动后报 "shared object initialization failed" | llama-server CUDA 库不匹配 | 删 `tools\*.dll` 留 exe 即可(纯 CPU) |
| 启动 OK 但首 token 30+ 秒 | ngl=99 + 显存不够 | 改 `ngl=0` |
| 输出乱码 / 中文乱 | 命令行编码 | `chcp 65001` + 终端 UTF-8 |
| OpenCode 报 connection refused | llama-server 没起 / 端口错 | `netstat -ano \| findstr 11435` |
| OpenCode 报 401 | apiKey 不匹配 | 改 `providers.json` 的 apiKey |
| 完全卡死 5+ 分钟 | ngl=0 + 3B + 8 线程,CPU 满载 | 正常,等;agent 循环 5 步最长 3 分钟 |

---

## 7. 性能调优速查 (CPU 路径)

按优先级排序:

| 调优项 | 影响 | 改法 |
|---|---|---|
| **ngl** | 0 = 100% CPU, 必须保持 0 | `startupArgs.ngl=0` |
| **context** | 8192 → 4096 = +30% | `startupArgs.context` |
| **threads** | 4 → 8 = +50% (8 核机器) | `startupArgs.threads` |
| **KV cache 量化** | q8_0 → q4_0 = +5-10% | llama-server `--cache-type-k q4_0` |
| **batch size** | 512 → 2048 = +15% | llama-server `-b 2048` |
| **换远程 GLM** | 3-10x 加速 | 启 newapi, 选 [2] |

---

## 8. 一键回收 (回到出厂配置)

```cmd
:: 1. 关掉所有本地 provider
stop-qwen.bat
netstat -ano | findstr ":11435 " | findstr LISTENING
:: 找到 PID 后: taskkill /PID <pid> /F

:: 2. 删掉 newapi (如果你启用了它)
:: 编辑 providers.json, 改 "newapi" 块的 enabled:true → false

:: 3. 回到 Qwen 默认
run.bat
```

---

## 9. 终极方案:双机协作

如果本机实在跑不动:

```
[内网机]   跑 qwen2.5-7B  (16+ GB 显存, GPU 加速)
    ↓ HTTP
[本机 vGPU 1Q]  OpenCode CLI 调用远程 API
```

也就是把 `providers.json` 的 baseURL 指向另一台内网机器的 llama-server。
不用改任何代码,只改 `baseURL` 一行。

---

## 10. FAQ

**Q: vGPU 1Q 完全不能跑 LLM 吗?**
A: 能, CPU 跑 3B 模型 8-10 tok/s 可用。4B+ OOM 或崩。

**Q: 我能强制用共享 GPU 内存吗?**
A: 不能。Windows vGPU 驱动对计算负载禁用共享内存, 这是设计而非 bug。

**Q: 换物理机 (16 GB + RTX 3060) 会快多少?**
A: qwen3-4b GPU 加速 6 GB 显存 vs CPU 16 GB RAM, 速度差 5-10 倍。

**Q: 0.5B 模型能用吗?**
A: 极速, 但 OpenCode 的工具调用成功率低 (实测 ~50% 错), 不推荐。

**Q: 我现在装哪一档模型?**
A: v2.3.5 锁死 **Qwen2.5-Coder-3B 本地** + **GLM-5.1 远程** 二选一。
   想要本地兜底 → 装 3B GGUF; 想要速度 → 启用 newapi 走内网 GLM。
