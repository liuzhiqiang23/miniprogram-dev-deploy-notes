# 微信小程序：从本地开发到云服务器上线的全流程笔记

> 一个真实课程的完整记录：把一个 Spring Boot + Vue 的影视数据管理与分析系统做成微信小程序，
> 并让**不在同一网络**的同学也能用。中间踩了内网穿透、正式小程序注册、请求域名白名单、
> ICP 备案、云服务器部署、HTTPS 证书等一整条链路的坑。
>
> 这份笔记按时间顺序拆成 7 个阶段，每个阶段都有：当时的判断 → 实测数据 → 踩到的坑 → 最终解法。

[![license](https://img.shields.io/badge/license-MIT-green)](LICENSE)

---

## 项目背景

- **后端**：Spring Boot 3.5（Java 21）+ MyBatis-Plus + MySQL + Redis，Undertow 容器
- **前端**：Vue3 管理后台（打包产物放进 jar 的 `static/`）
- **小程序端**：原生小程序（会员 / 优惠券 / 订单 / 影片浏览），无跨端框架
- **数据量**：约 4900 部影片、5000+ 张海报（437 MB）

目标只有一个：**同学在宿舍、在家里、用流量，都能打开这个小程序看到真数据。**

---

## 最终架构

```
                     微信小程序（体验版/正式版）
                              │  wx.request  https
                              ▼
                 ┌────────────────────────────┐
                 │  云服务器（大陆机房，需备案）  │
                 │  nginx :443                 │
                 │   ├── /posters/  → 读磁盘    │  ← 437MB 海报不进 jar
                 │   └── /          → 127.0.0.1:8000
                 │  Spring Boot (systemd)      │
                 │  MySQL 8.4 / Redis 8        │
                 └────────────────────────────┘
```

---

## 全流程分阶段

| 阶段 | 干什么 | 文档 |
|---|---|---|
| 一 | 本地开发，手机连热点真机联调 | [docs/01-local-dev.md](docs/01-local-dev.md) |
| 二 | 内网穿透，让外网临时访问 | [docs/02-tunnel.md](docs/02-tunnel.md) |
| 三 | 注册正式小程序（测试号的局限、名称审核、凭证管理） | [docs/03-registration.md](docs/03-registration.md) |
| 四 | 体验版与「请求合法域名」的硬门槛 | [docs/04-whitelist.md](docs/04-whitelist.md) |
| 五 | 部署到云服务器（本笔记的大头） | [docs/05-server-deploy.md](docs/05-server-deploy.md) |
| 六 | 备案实录：域名备案 ≠ 小程序备案 | [docs/06-icp.md](docs/06-icp.md) |
| 七 | 用 CLI 上传代码（绕开 Electron 鼠标模拟失效） | [docs/07-cli-upload.md](docs/07-cli-upload.md) |
| 附 | 踩坑清单总表 | [docs/pitfalls.md](docs/pitfalls.md) |

---

## 最重要的十条经验

1. **内网穿透只能救急，不能当正式方案。** 免费隧道速度受固定延迟支配（实测绕美国 260ms 单程，
   399 字节的响应也要 1.2 秒），而且你电脑一关机全体掉线。
2. **小程序的「请求合法域名」是 HTTPS + ICP 备案 + 不能用 IP，三条都是硬的。**
   开发者工具里勾「不校验合法域名」只对开发版/预览版有效，**体验版和正式版必查**。
3. **注册小程序名称时，纯通用词必被拒**（「电影票务演示」被拒）。
   规律：自造词打头 + 业务词收尾 = 容易过。
4. **git HEAD 落后于工作区时，`git clone` 出来构建的是一个坏包。**
   我们这边 HEAD 里还是模板作者硬编码的 appid，环境变量根本覆盖不了，微信登录会**静默**退回演示模式。
5. **`-DskipTests` 不够，部署构建要用 `-Dmaven.test.skip=true`。**
   前者只跳过执行不跳过编译，测试依赖解析不到会直接挂。
6. **几百 MB 的静态资源不要打进 Spring Boot jar。** 用 nginx 直接读磁盘，
   一个 `location` 就解决了，构建产物从 460MB 缩回 80MB。
7. **凭证绝不进代码库。** 用 systemd 的 `EnvironmentFile`（chmod 600）注入
   `WX_APPID / WX_SECRET`，`application.yml` 里只写 `${WX_APPID:}` 占位符。
8. **备案是两件事**：域名备案（工信部，给网址）和小程序备案（工信部，给小程序本身）。
   互不替代，都要做。
9. **备案驳回很常见**，九成是「网站备注」没写清性质/内容/用途，改一句话重新提交即可，
   不是否决。千万别在备注里写「影视/视频」，会引来《信息网络传播视听节目许可证》的追问。
10. **微信开发者工具的窗口点不动鼠标（Electron），但 CLI 全都能做。**
    `cli.bat upload --project xxx -v 1.0.1 -d "desc"` 一条命令完成上传。

---

## 目录结构

```
.
├── README.md
├── docs/                    # 7 个阶段 + 踩坑清单
├── deploy/
│   ├── movie-system.service # systemd 单元模板
│   └── nginx-miniprogram.conf  # nginx 反代 + 静态资源模板
└── scripts/
    ├── ssh_run.py           # SSH 远程执行助手（密码只走环境变量，不落盘）
    └── push_env.py          # 把本机环境变量里的密钥推成服务器上的 600 权限 env 文件
```

---

## 安全与脱敏说明

- 文中所有服务器地址、域名一律用 `203.0.113.10` / `example.cn` 占位
- **不包含**任何 AppSecret、数据库口令、个人身份证信息
- 服务器上的密钥文件权限为 `600`，且由脚本从本机环境变量推送生成，从未提交进 git

## License

[MIT](LICENSE)
