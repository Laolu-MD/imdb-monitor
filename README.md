# IMDb Rating Monitor (轻量 CSV 版)

每天自动检查你 watchlist 中电影的 IMDb 评分变化，并补充导演、演员、国家、语言、体裁、评级、票房等静态信息。

## 文件说明

- `watchlist.csv`：你的电影列表（用 Excel / Google Sheets 打开编辑）
- `monitor.py`：主脚本
- `rating_history.csv`：评分历史记录（自动生成）
- `metadata_cache.json`：静态元数据缓存（自动生成）
- `latest_report.txt`：最新变化报告（自动生成）
- `.github/workflows/imdb-monitor.yml`：GitHub Actions 定时任务

## watchlist.csv 字段

| 字段 | 说明 | 示例 |
|------|------|------|
| imdb_id | IMDb ID（必填，如 tt0111161） | tt0111161 |
| title | 片名（可选，脚本会自动补充） | The Shawshank Redemption |
| watched | 是否已观看 | yes / no |
| priority | 优先级（数字，越大越重要） | 5 |
| in_library | 是否已在片库 | yes / no |
| notes | 备注 | 经典必看 |

## 本地运行（可选）

```bash
export OMDB_API_KEY=你的key
python monitor.py
```

## GitHub Actions 部署步骤

1. 新建一个 GitHub 仓库（公开或私有均可）。
2. 把以下文件上传到仓库根目录：
   - `monitor.py`
   - `watchlist.csv`（先编辑好你的电影）
   - `requirements.txt`
   - `.github/workflows/imdb-monitor.yml`（注意目录结构）
3. 在仓库 Settings → Secrets and variables → Actions 中添加 Secret：
   - 名称：`OMDB_API_KEY`
   - 值：你的 OMDb API Key
4. 进入 Actions 页面，确认 workflow 已启用。
5. 可手动点击 "Run workflow" 测试一次。

之后每天会自动运行，并把更新后的文件提交回仓库。你可以直接在 GitHub 网页查看 `latest_report.txt`，或下载 CSV 用 Excel 打开。

## 额度说明

- 评分检查使用免费的 Agregarr API（无需 Key）。
- OMDb 只在首次出现或缓存超过 180 天时才调用，日常几乎不消耗额度。

## 注意事项

- 公开仓库如果 60 天没有任何活动，定时任务会被 GitHub 自动暂停，偶尔手动触发或提交一次即可恢复。
- 定时任务可能有几分钟到几十分钟的延迟，属正常现象。
- 请妥善保管 OMDb API Key，不要提交到代码中。
