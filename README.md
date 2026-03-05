# S.H.I.T Journal 备份爬虫

从 [shitjournal.org](https://shitjournal.org/) 定期抓取**新闻**与**预印本**文章，并备份为 Markdown 与 JSON 元数据到本仓库。

## 功能

- 抓取 **新闻** 列表下所有文章（如公告、征稿、简讯等）
- 抓取 **预印本** 列表中的详情页（若站点提供链接）
- 每篇文章保存为：`backup/{news|preprints}/{slug}.md` 与 `{slug}.meta.json`
- 生成 `backup/index.json` 索引，便于去重与检索
- 使用礼貌间隔与固定 User-Agent，避免对目标站造成压力

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 仅抓取新闻
python crawler.py crawl --news-only

# 抓取新闻 + 预印本（默认）
python crawler.py crawl

# 指定输出目录与请求间隔
python crawler.py crawl -o ./my_backup --delay 1.5
```

## GitHub Actions 每日备份

仓库内已配置 `.github/workflows/daily-backup.yml`：

- **触发**：每天 UTC 00:00（北京时间 08:00）定时运行；也可在 Actions 页手动 `Run workflow`。
- **步骤**：检出仓库 → 安装 Python 与依赖 → 运行爬虫 → 若有变更则 commit 并 push 到当前分支。

首次使用请确保：

1. 仓库为**公开**（你已说明）。
2. 默认分支（如 `main`）具有写入权限；若在分支 `backup` 上跑，请把 workflow 里的 `git push` 目标改为对应分支。

如需修改推送分支或 cron 时间，直接编辑 `.github/workflows/daily-backup.yml` 中的 `schedule` 与 `branches` 即可。

## 目录结构

```
shitjournal-backup/
├── .github/workflows/
│   └── daily-backup.yml   # 每日备份 workflow
├── backup/
│   ├── index.json         # 本次抓取索引
│   ├── news/              # 新闻文章 .md + .meta.json
│   └── preprints/         # 预印本文章（若有）
├── crawler.py             # 爬虫入口
├── requirements.txt
└── README.md
```

## 许可与免责

本工具仅供个人备份与学习使用。请遵守 shitjournal.org 的访问条款与 robots.txt；若对方要求停止抓取，请立即停止使用。
