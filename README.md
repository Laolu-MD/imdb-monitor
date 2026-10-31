# IMDb High Score Monitor + 查看页面

每天自动从 IMDb 官方数据集生成高分电影完整清单，并提供一个可在 GitHub Pages 上运行的查看页面。

## 功能

- 每日全量高分电影清单（历史老片只要当前达标就会出现）
- 自动记录新上榜、评分变化、掉出
- 静态查看页面：搜索、排序、筛选
- 本地记录已观看 / 优先级 / 备注（保存在浏览器，不上传）

## 文件

- `monitor.py` — 数据生成脚本
- `.github/workflows/imdb-monitor.yml` — 定时任务
- `index.html` — 查看页面（GitHub Pages）
- `README.md`

## 部署步骤

1. 新建公开仓库，上传所有文件
2. 在 Settings → Secrets 添加 `OMDB_API_KEY`（可选）
3. 启用 Actions
4. 进入 Settings → Pages，选择 `main` 分支 / root 作为源
5. 修改 `index.html` 里的 `REPO_RAW` 为你的仓库地址：
   ```js
   const REPO_RAW = "https://raw.githubusercontent.com/你的用户名/仓库名/main/";
   ```
6. 访问 `https://你的用户名.github.io/仓库名/` 即可查看

个人标记（已观看、优先级、备注）保存在浏览器本地，清除浏览器数据会丢失。
