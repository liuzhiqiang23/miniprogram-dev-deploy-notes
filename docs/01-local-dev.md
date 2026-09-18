# 阶段一：本地开发与真机联调

## 目标

在开发者工具里跑通之后，让**开发者本人的手机**也能访问本机后端。

## 网络拓扑

```
手机（微信）
   │  同一个局域网（电脑开热点给手机，或都连同一个路由器）
   ▼
电脑：Spring Boot 监听 0.0.0.0:8000
```

## 做法

`app.js` 里维护一个候选地址数组，启动时**并发探测**，谁通用谁：

```js
const API_BASES = [
  'http://127.0.0.1:8000',      // 开发者工具模拟器（跑在本机）
  'http://192.168.83.214:8000', // 局域网 IP（手机连电脑热点时）
  'https://xxxx.trycloudflare.com' // 公网隧道（见阶段二）
];

function probe(base) {
  return new Promise(resolve => {
    wx.request({
      url: base + '/api/wx/member/plans',
      method: 'POST', data: {},
      header: { 'Content-Type': 'application/json' },
      timeout: 2500,                     // 必须短，见下面的坑
      success: () => resolve({ base, ok: true,  err: '' }),
      fail:    e  => resolve({ base, ok: false, err: (e && e.errMsg) || 'unknown' })
    });
  });
}

function pickBase(app) {
  return Promise.all(API_BASES.map(probe)).then(rs => {
    // 把每个地址的探测结果记下来，出错时弹给用户看
    app.globalData.probeDiag = rs.map(r =>
      (r.ok ? '[通]   ' : '[不通] ') + r.base + (r.err ? '  ' + r.err : '')).join('\n');
    for (const r of rs) if (r.ok) return r.base;
    return API_BASES[API_BASES.length - 1];
  });
}
```

请求层在发请求前 `await` 探测结果，但**最多等 1.5 秒**：

```js
const bounded = Promise.race([ app.ready(), new Promise(r => setTimeout(r, 1500)) ]);
```

## 踩到的坑

### 1. 局域网地址会把整页请求拖死

校园网是 `/20` 的大网段，普遍做了**客户端隔离**：手机 ping 得通网关，但连不到电脑。
后果是那条局域网候选要挂满 TCP 超时（可能 60 秒）才失败，而 `Promise.all` 会等它。

**解法**：探活超时压到 2.5 秒 + 请求层用 `Promise.race` 兜底 1.5 秒。

### 2. 热点重启会换网段

手机热点每次开关，分配给电脑的 IP 可能从 `192.168.43.x` 变成 `192.168.83.x`。
写死在代码里的局域网 IP 就成了过期地址。

**解法**：写一个脚本在启动后端时自动把当前 IP 回写进 `app.js`
（PowerShell 里用 `Get-NetIPConfiguration | Where IPv4DefaultGateway` 拿默认网段所在网卡的 IPv4）。

### 3. 真机上 `<image>` 不加载 http 图片

开发者工具里好好的，真机上图片全空。原因是真机对 http 域名的图片有更严格的限制。

**解法**：图片走 `wx.downloadFile` 拿到 `tempFilePath` 再塞给 `<image>`。

### 4. 排查"连不上后端"的套路

真机上没地方看 console，把三条信息一次性弹出来最快：

```js
wx.showModal({
  title: '连不上后端',
  content: '请求地址：\n' + url +
           '\n\n微信错误：\n' + errMsg +
           '\n\n候选地址探测：\n' + probeDiag,
  showCancel: false
});
```

最常见的原因：**换了网络，`app.js` 里的局域网 IP 过期了**。

---

➡️ 下一阶段：[内网穿透](02-tunnel.md)
