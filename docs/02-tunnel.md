# 阶段二：内网穿透（cloudflared 免费隧道）

## 为什么需要

同学不在你的局域网里，局域网 IP 对他们毫无意义。需要一个「公网能访问、又不用买服务器」的临时方案。

`cloudflared` 的 quick tunnel 免费且不需要注册账号，一条命令就能把本机端口暴露到公网：

```
浏览器 → Cloudflare 边缘节点 → 隧道 → 你电脑上的 127.0.0.1:8000
```

## 命令

```bash
cloudflared.exe tunnel --url http://localhost:8000 \
  --no-autoupdate \
  --edge-ip-version 4 \
  --protocol http2 \
  --logfile tunnel.log --loglevel info
```

启动后从 `tunnel.log` 里解析出分配的域名（形如 `https://xxxx-xxxx.trycloudflare.com`）。

## ⚠️ 四个必须注意的坑

### 1. 默认走 IPv6，会卡死在 "Requesting new quick Tunnel"

必须加 `--edge-ip-version 4`。

### 2. QUIC 协议在国内部分线路上不通

加 `--protocol http2`。

### 3. 直接 `Start-Process cloudflared.exe` 会静默死掉

必须包一层 `.cmd` 再启动：

```bat
@echo off
cd /d D:\tools
cloudflared.exe tunnel --url http://localhost:8000 --no-autoupdate --edge-ip-version 4 --protocol http2 --logfile tunnel.log
```

```
Start-Process cmd.exe -ArgumentList '/c','tunnel.cmd' -WorkingDirectory 'D:\tools' -WindowStyle Minimized
```

### 4. 脚本顺序错误会两头空

先杀旧隧道再申请新域名，一旦 Cloudflare 限流，旧域名已经没了、新的又没拿到，**两头空**。

**正确顺序**：先启动新隧道 → 从日志解析出新 URL → 写回 `app.js` → **最后**才杀旧进程。

## 实测性能：瓶颈是固定延迟，不是带宽

| 测试 | 结果 |
|---|---|
| 单次请求（399 字节 JSON） | **1.2 ~ 1.3 秒** |
| 缩小响应体 36 倍（61KB → 5KB） | 耗时几乎不变（51s vs 69s 的批量测试） |
| 中国移动把 Cloudflare 路由到 | **洛杉矶（lax01）**，单程 260ms |
| 丢包 | 0% |
| 上行带宽 | 550 KB/s |

结论：**数据量再小也快不起来，因为每次都要绕美国一圈。** 做缩略图、压缩字段都是无效优化。

## 免费隧道的固有限制

- 免费版锁死 `ha-connections: 1`，并发一高就超时
- 域名随机，**每次重启都换**
- **电脑关机 = 全体掉线**，这是它只能当临时方案的根本原因

## 后来的实测对比

部署到云服务器之后（见[阶段五](05-server-deploy.md)）：

| | 内网穿透 | 云服务器 |
|---|---|---|
| 同一个接口 | 1.2 s | **0.04 s**（差约 30 倍） |
| 电脑关机后 | ❌ | ✅ |

---

➡️ 下一阶段：[注册正式小程序](03-registration.md)
