# 阶段七：用 CLI 上传代码

## 为什么不用图形界面

微信开发者工具是 Electron 应用。在 Windows 上对它做 GUI 自动化时：

- `SetCursorPos` / `mouse_event` / `SendInput` 鼠标模拟 **全部无效**
- `SendKeys` 键盘**有效**（`Ctrl+B` 能编译）

所以「点右上角上传按钮」这条路走不通，但**官方 CLI 能做所有事**。

## 前置条件

- 工具已安装（`D:\微信开发者工具\`）
- **IDE 的服务端口要打开**：关掉 IDE，改 localstorage 的 `security.enableServicePort`
  为 `true`，再启动
- 已经用微信扫过码登录过（session 还在就不用重新扫）

## 常用命令

```bat
cd /d D:\微信开发者工具

:: 是否登录
cli.bat islogin --project D:\project\miniprogram

:: 上传（版本号 + 备注）
cli.bat upload --project D:\project\miniprogram -v 1.0.1 -d "point API base to movie server"

:: 生成预览二维码
cli.bat preview --project D:\project\miniprogram

:: 打开项目
cli.bat open --project D:\project\miniprogram

:: 编译 npm（有依赖时）
cli.bat build-npm --project D:\project\miniprogram
```

实际输出长这样：

```
✔ IDE server has started, listening on http://127.0.0.1:17464
{"login":true}
✔ Using AppID: wx0ce243dae842cc7e
 TOTAL  70.9 KB
✔ upload
```

## 一个 Windows 特有的坑

`.ps1` 脚本里写**中文路径**会挂：PowerShell 5.1 默认按系统代码页（GBK）读无 BOM 的 UTF-8 脚本，
`微信开发者工具` 会变成乱码，报「无法将 xxx 项识别为 cmdlet」。

**解法**：别在脚本里写中文路径。在 bash 里 `cd` 过去再调，参数保持纯 ASCII：

```bash
cd "/d/微信开发者工具" && cmd //c "cli.bat upload --project D:\\project\\miniprogram -v 1.0.1 -d desc"
```

同理，`.bat` 脚本必须 **纯 ASCII + CRLF 换行**——cmd.exe 对 LF-only 或含中文的批处理
解析会错位（症状可能是命令被啃掉一半）。

## 上传之后

小程序后台 → **管理 → 版本管理** → 「开发版本」里能看到刚传的版本 → 点「选为体验版」
→ 生成体验版二维码（只有项目成员和体验成员能打开）。

---

➡️ 返回 [踩坑清单](pitfalls.md)
