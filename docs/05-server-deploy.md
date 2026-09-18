# 阶段五：部署到云服务器（本笔记的大头）

## 0. 服务器要求

小程序的合法域名要求域名**经过 ICP 备案**，而个人/企业的域名备案只能挂在**中国大陆的机房**上。
所以服务器必须选大陆节点（腾讯云 / 阿里云轻量等）。

> 拿不到大陆服务器，就只能走「微信云托管」（`wx.cloud.callContainer`，不占合法域名名额），
> 代价是按量计费 + 后端要容器化。

本例的环境：

```
Ubuntu 26.04 LTS · 4 核 · 3.6 GB 内存 · 40 GB 盘
```

## 1. 上去第一件事：只读体检，什么都别改

```bash
hostname; id; cat /etc/os-release | grep PRETTY; nproc; uptime
free -h
df -h | grep -vE '^(tmpfs|overlay)'
ss -tlnp            # 看哪些端口被占了
systemctl list-units --type=service --state=running --no-pager
ls -l /etc/nginx/sites-enabled/ 2>/dev/null
```

这一步是为了搞清楚：**这台机器上有没有别人的东西**。
借来的服务器尤其重要——别一上来就 `apt install`，先把风险点列给对方确认。

## 2. 装依赖

Ubuntu 自带的源在云内网走镜像，非常快：

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  openjdk-21-jdk-headless maven mysql-server redis-server nginx \
  certbot python3-certbot-nginx rsync jq
```

MySQL 8.4 注意：默认认证插件是 `caching_sha2_password`，JDBC URL 里要有
`allowPublicKeyRetrieval=true`（本项目本来就有）。

## 3. 建库导数据

**不要拿仓库里那份 SQL dump 直接用**——它往往是老的。从本机现导一份：

```bash
mysqldump -uroot -p --single-transaction --default-character-set=utf8mb4 \
  --routines --triggers --events --hex-blob --set-gtid-purged=OFF \
  vidio_mangage_db > movie_db_full.sql
```

服务器上建**专用账号**，别用 root：

```sql
CREATE DATABASE vidio_mangage_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER 'movie'@'localhost' IDENTIFIED BY '<强口令>';
GRANT ALL PRIVILEGES ON vidio_mangage_db.* TO 'movie'@'localhost';
FLUSH PRIVILEGES;
```

导入后顺手清掉开发期的测试数据（我们删了 61 个 `demo_openid_*` 占位用户）。

## 4. 静态资源：不要打进 jar

海报有 **437 MB / 5011 个文件**。如果放在 `src/main/resources/static/` 里，
Maven 会原样拷进 `target/classes`，最终打出一个 **460 MB 的 jar**——启动慢、传输慢、每次构建都痛苦。

**解法：海报不进 jar，由 nginx 直接读磁盘。** URL 一个字都不用改：

```nginx
location ^~ /posters/ {
    root /opt/movie-system;     # /posters/1.jpg → /opt/movie-system/posters/1.jpg
    expires 30d;
    try_files $uri @backend;    # 磁盘上没有就回落给 Spring，保持同一种错误格式
}
```

传 437 MB 用 **tar 流式管道**，本地不留临时文件：

```bash
tar cf - -C /path/to/project --exclude='backend/target' \
    --exclude='backend/src/main/resources/static/posters' backend \
  | ssh ubuntu@203.0.113.10 "mkdir -p /opt/app && tar xf - -C /opt/app"
```

实测 437 MB 走家用宽带上行约 **2 分半**。

## 5. ⚠️ 构建最大的坑：git HEAD 落后于工作区

我们最初的方案是「服务器上 `git clone` 再 `mvn package`」，结果得到一个**坏包**：

- HEAD 里的 `application.yml` 还是模板作者**硬编码的 appid**，没有 `${WX_APPID:}` 占位符
  → 环境变量**根本覆盖不了** → 微信登录**静默退回演示模式**，不报任何错
- HEAD 里缺三行接口白名单 → 分类、搜索接口全部 401

症状是「一部分接口报用户未登录」，非常隐蔽。

**结论：部署必须用工作区的源码，不能图省事 clone。**
验证方法很简单——部署完把本地和线上各调一遍同样的接口，逐字节对比：

```python
# 本地 vs 线上，SAME 才算部署忠实
for path, body in CASES:
    assert call('http://127.0.0.1:8000', path, body) == call('https://api.example.cn', path, body)
```

我们 9 个接口全部 `SAME` 才敢往下走。

## 6. ⚠️ 第二个坑：`-DskipTests` 不够

```
mvn -DskipTests package     # ❌ 只跳过「执行」，还是要编译测试代码
mvn -Dmaven.test.skip=true package   # ✅ 连编译一起跳
```

测试树里 junit 解析不到时，前者会报一堆 `cannot find symbol: class Test`。

## 7. systemd 服务

```ini
[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/movie-system/run
EnvironmentFile=/opt/movie-system/movie.env      # 密钥在这里，chmod 600
Environment=SPRING_PROFILES_ACTIVE=dev
Environment=JAVA_TOOL_OPTIONS=-Xms256m -Xmx1024m -XX:MaxDirectMemorySize=256m -Dfile.encoding=UTF-8
ExecStart=/usr/bin/java -jar /opt/movie-system/run/app.jar
Restart=always
RestartSec=5
```

`movie.env` 长这样（**绝不提交进 git**）：

```
SPRING_DATASOURCE_USERNAME=movie
SPRING_DATASOURCE_PASSWORD=...
WX_APPID=wx...
WX_SECRET=...
WX_ADMIN_OPEN_IDS=oXXXX...
SERVER_ADDRESS=127.0.0.1     # 只监听本机，对外一律走 nginx
```

推送到服务器时**不要让密钥经过命令行**——用脚本从本机环境变量读，SFTP 直接写文件：

见 [scripts/push_env.py](../scripts/push_env.py)。

最后别忘了日志轮转（MyBatis 开着 SQL 全量打印，一次启动能刷 9 MB）：

```
# /etc/logrotate.d/movie-system
/opt/movie-system/run/app.log /opt/movie-system/run/log/*.log {
    daily rotate 7 maxsize 200M missingok notifempty compress delaycompress copytruncate
    su ubuntu ubuntu
}
```

## 8. nginx 反代

完整配置见 [deploy/nginx-miniprogram.conf](../deploy/nginx-miniprogram.conf)，要点：

- `server_name` 里**同时写域名和裸 IP**——域名还没解析的那段时间，真机预览版只能靠 IP 连，
  而此时请求的 `Host` 头就是 IP 本身，不写就会落到 default 站点上返回 404
- `/.well-known/acme-challenge/` 必须留在 80 端口，Let's Encrypt 的 HTTP-01 验证要用
- 其余全部 `proxy_pass http://127.0.0.1:8000`

申请证书（需要 DNS 已生效）：

```bash
sudo certbot --nginx -d api.example.cn
```

## 9. 验证清单

```bash
# 外网连通性
curl -s -X POST https://api.example.cn/api/wx/member/plans -H 'Content-Type: application/json' -d '{}'
# 静态资源
curl -sI https://api.example.cn/posters/1.jpg | head -3
# 微信登录链路是否真的用了自己的 appid（而非模板作者的）
sudo tr '\0' '\n' < /proc/$(pgrep -f app.jar)/environ | grep WX_APPID
```

最后一条是关键：如果代码里在 appid 等于模板作者默认值时会**退回演示模式**，
那么"接口返回正常"并不能证明凭证生效，必须看进程环境里到底是什么。

---

➡️ 下一阶段：[备案实录](06-icp.md)
