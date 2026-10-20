# Tailscale · 手机进中枢的私有通道

> 目标：手机不在同一局域网也能安全访问你 PC 上的私有平台（看板 / 外部门户 / 找球球办事）。
> 原则：P2P 加密、仅你的设备、零订阅、不暴露公网端口。

## 步骤
1. PC 与手机都装 Tailscale（免费个人版）：
   - PC（Windows）：https://tailscale.com/download/windows
   - 手机：App Store / 应用商店搜 Tailscale
2. 两边用同一账号登录，设备自动组网，各得一个 `100.x.x.x` 的 Tailscale IP。
3. PC 上把私有平台服务绑到 `0.0.0.0`（或 Tailscale 接口），例如 Next.js `next dev -H 0.0.0.0 -p 3000`。
4. 手机浏览器访问 `http://<PC的TailscaleIP>:3000` 即可。
5. （可选）在 PC 上设 `tailscaled` 开机自启，保证中枢常开。

## 校验
- PC 执行 `tailscale ip` 拿到本机 Tailscale IP。
- 手机切到蜂窝网络（关 WiFi），访问该 IP:端口，能打开即通。

## 备选
- 若不想装 Tailscale：用 Cloudflare Tunnel / frp 做反向隧道（仍不暴露真实 IP，但走第三方中继）。
- 纯局域网场景可先用局域网 IP，后续再上 Tailscale。
