# 电影清单资源助手

在 Edge 或 Chrome 中安装一次，电影清单页面即可通过浏览器向 SeedHub 请求影片和资源；勾选版本后自动添加磁力链接，下载文本清单。

1. 下载 [完整项目 ZIP](https://github.com/Laolu-MD/imdb-monitor/archive/refs/heads/main.zip) 并解压。
2. Edge 打开 `edge://extensions`，打开“开发人员模式”，选择“加载解压缩的扩展”。
3. 选择解压目录中的 `film_extension` 文件夹。Chrome 操作类似，在 `chrome://extensions` 选择“加载已解压的扩展程序”。
4. 打开或刷新 [电影清单](https://laolu-md.github.io/imdb-monitor/)，在“查找影片资源”中输入中文片名，点击搜索；选择影片并核对年份，再选择资源版本。
5. 点击“加入磁力清单”，可继续选择多个版本；点击“下载磁力链接列表”。在 Download Station 的“添加任务→输入 URL”中粘贴文本内容。

助手只对指定电影清单页面生效，仅向 SeedHub 读取公开网页，不读取 NAS 账号、密码或电影账号。查询时影片名称会发送至 SeedHub，SeedHub 可能接收浏览器已有的该站 Cookie。扩展不会自动创建 NAS 下载任务。

SeedHub 可能要求验证或拒绝自动请求。出现提示时，请先在浏览器打开 SeedHub 并按网站正常流程操作；如果扩展仍无法读取，页面会显示错误。请使用你有权获取的资源。

项目附带的自动化测试使用模拟网页；实际站点可能变更。
