# 想看电影资源助手

Windows 本地工具，使用 Python 3.9 或更新版本（安装 Python 时包含 tkinter）。不需要额外 Python 包。

1. 在电影清单点击“导出想看清单”，保存 CSV。
2. 下载本目录，双击 `start.bat`，或者在此目录运行 `py movie_helper.py`。
3. 点击“导入想看 CSV”，选择文件。“查询全部想看”会逐部请求 SeedHub。英文无结果时，输入中文片名单独查询。
4. 在候选中选中影片，点“打开候选网页核对”确认片名和年份，双击候选加载资源列表。多选版本后获取磁力并加入队列。
5. 可选择“复制全部磁力”，到 Download Station 的“添加任务 → 输入 URL”批量粘贴；也可点击“发送至 Download Station”，按提示填写 NAS 信息。

自动发送要求 NAS 的 HTTPS 已启用。现有自签名证书可通过 SHA-256 指纹验证，不需要将其作为受信任根证书导入系统：请从可信来源取得原有 NAS 服务器**公钥证书**，独立核对其 SHA-256 指纹；指纹不符时程序不会发送登录信息。Windows PowerShell 可计算 PEM 证书的指纹（将路径改为你的证书文件）：

```powershell
$pem = Get-Content -Raw 'C:\path\to\certificate.crt'
$body = ($pem -split '-----BEGIN CERTIFICATE-----')[1] -split '-----END CERTIFICATE-----' | Select-Object -First 1
$der = [Convert]::FromBase64String(($body -replace '\s',''))
[BitConverter]::ToString([Security.Cryptography.SHA256]::Create().ComputeHash($der)).Replace('-','')
```

仅输入公钥证书路径，勿上传或分享私钥。核对指纹须依靠可信来源；对未经验证的现场连接直接抄指纹无法防御中间人攻击。每次重新连接都会验证指纹。管理员账号和密码仅在本次运行内用于访问局域网 NAS，不写文件或 GitHub；工具不接受公网地址。它们通过加密的 HTTPS 发给 NAS。关闭工具后需重新输入。

工具使用 Download Station V5 接口，可能因 QTS 设置、两步验证、权限或接口差异而登录失败；可以用“复制全部磁力”方案。发送结果为服务端接口返回的接受情况，实际下载进度请在 Download Station 查看。该版本没有向真实 NAS 发送测试任务；提供了模拟测试：`py -m unittest discover -s . -v`。

搜索与解析依赖 SeedHub 当前页面结构和访问状态，可能遇到网站验证或片名不匹配；请人工确认影片与版本。查询影片时搜索词会发送给 SeedHub。网站不可访问时可手动使用其网页。请仅下载你有权获取的内容。
