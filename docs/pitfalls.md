# 踩坑清单（按出现顺序）

| # | 现象 | 真正原因 | 解法 |
|---|---|---|---|
| 1 | 手机上局域网地址要等 60 秒才失败，整页请求被拖死 | 校园网 `/20` 网段做客户端隔离，TCP 挂到超时 | 探活超时压到 2.5s，请求层 `Promise.race` 兜底 1.5s |
| 2 | 热点重启后小程序连不上 | `app.js` 里的局域网 IP 过期了 | 启动脚本自动探测当前 IP 回写 |
| 3 | 真机图片全空 | 真机对 http 图片限制更严 | `wx.downloadFile` 拿 `tempFilePath` |
| 4 | cloudflared 卡在 `Requesting new quick Tunnel` | 默认走 IPv6 | `--edge-ip-version 4` |
| 5 | cloudflared 隧道建不起来 | QUIC 在部分国内线路不通 | `--protocol http2` |
| 6 | 用脚本启动 cloudflared 后进程没了 | 直接 `Start-Process` exe 会静默死 | 包一层 `.cmd`，用 `Start-Process cmd.exe /c` 启动 |
| 7 | 杀旧隧道 + 申请新隧道两头空 | 先杀后申请，遇限流就都没了 | 先拿到新 URL 写回代码，**最后**杀旧进程 |
| 8 | 隧道慢，以为是图片太大 | 实测数据量砍 36 倍耗时不变 | 瓶颈是绕美国的**固定延迟**，压缩无效，换服务器 |
| 9 | 注册名称「电影票务演示」被拒 | 纯通用词，无显著识别性 | 自造词打头 + 业务词收尾 |
| 10 | 换 AppID 后管理员身份丢了 | **openid 跟着 AppID 走**，换了就变 | 新号重新登录拿新 openid，更新 `WX_ADMIN_OPEN_IDS` |
| 11 | 体验版报 `request:fail invalid url` | 合法域名要求 HTTPS + 备案 + 非 IP，体验版必查 | 上备案域名；「不校验合法域名」只对开发/预览版有效 |
| 12 | 同学扫码报「暂无体验权限」 | 体验版只有成员能开 | 后台加「体验成员」 |
| 13 | 服务器上构建出的包，微信登录**静默**退回演示模式 | `git clone` 的是 HEAD，而 HEAD 里的 appid 是硬编码、没接环境变量 | 部署用**工作区源码**；部署后对比本地/线上接口响应 |
| 14 | 服务器 `mvn package` 报 `cannot find symbol: class Test` | `-DskipTests` 只跳执行不跳编译 | 用 `-Dmaven.test.skip=true` |
| 15 | jar 从 72MB 涨到 460MB | 437MB 海报被 Maven 拷进 `resources/static` | 海报不进 jar，nginx 读磁盘 |
| 16 | 访问 `/posters/1.jpg` 返回 404 | 裸 IP 访问时 `Host` 头是 IP，落到了 default 站点 | `server_name` 同时写域名和裸 IP |
| 17 | 日志一次启动涨 9.5MB | MyBatis `StdOutImpl` 全量打印 SQL 参数 | logrotate + 关闭 SQL 打印 |
| 18 | 后端 8000 端口对公网开着 | Spring 默认监听所有网卡 | `SERVER_ADDRESS=127.0.0.1`，对外只走 nginx |
| 19 | 备案被驳回 | 「网站备注」没写清性质/内容/用途 | 按模板补一句说明，重新提交即可 |
| 20 | 域名怎么都打不开，返回 302 到 qcloud 页面 | 腾讯云在**网络层**劫持未备案域名 | 无解，只能等备案 |
| 21 | `.ps1` 里的中文路径报「无法识别」 | PowerShell 5.1 按 GBK 读无 BOM 的 UTF-8 脚本 | 脚本别写中文路径；`cd` 过去再调用 |
| 22 | `.bat` 脚本执行时命令被啃掉一半 | cmd.exe 对 LF-only 或含中文的批处理解析错位 | 批处理一律 **纯 ASCII + CRLF** |
| 23 | 开发者工具点不动鼠标 | Electron 窗口，`SetCursorPos`/`SendInput` 全失效 | 用官方 **CLI**（`cli.bat upload`） |
| 24 | 忘了服务是否真的在跑 | 凭感觉下结论 | **先拿活证据**：`/proc/<pid>/environ`、`systemctl status`、真实请求 |

---

## 三条贯穿始终的原则

1. **先测量，再下结论。** 隧道慢那次，压缩数据量之前先跑了基准测试，才发现瓶颈是延迟不是带宽。
2. **部署完必须做差异验证。** 「接口返回 200」不等于「部署忠实」，本地和线上逐字节对比才算数。
3. **断言"已生效"之前先拿活证据。** 环境变量是否真的进了进程、配置是否真的被加载，
   都要看 `/proc`、`nginx -T`、`systemctl status`，而不是看代码里写了什么。
