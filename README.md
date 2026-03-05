# S.H.I.T Journal 归档

本仓库对 [S.H.I.T Journal](https://shitjournal.org/) 的**新闻**与**预印本**进行定期同步与长期归档，以 Markdown 与 JSON 元数据形式保存，便于引用与离线访问。

## 目标

- **长期保存**：为社区期刊内容提供可追溯的存档副本。
- **学术可引用**：每篇条目含 URL、标题、作者、单位、学科、提交时间等元数据，便于引用与检索。
- **去中心化备份**：公开仓库中的归档不依赖单一站点可用性。

## 来源与收录范围

| 类型 | 说明 |
|------|------|
| **新闻 / News** | 公告、征稿启事、新功能说明、简讯等。 |
| **预印本 / Preprints** | 社区投稿文章，按刊物流程分为：旱厕 → 化粪池 → 构石 → 沉淀区。 |

仅收录上述两类内容的正文与元数据；首页、子刊导航等不在收录范围内。

## 浏览归档（GitHub Pages）

仓库内已包含静态站点（`docs/index.html` + `docs/assets/style.css`），用于在 GitHub Pages 上展示归档目录。**首次使用需在仓库设置中开启 Pages**：

1. 打开 **Settings → Pages**
2. **Source** 选择 **Deploy from a branch**
3. **Branch** 选 `main`，**Folder** 选 **/docs**
4. 保存后等待部署，站点地址为：**https://xx025.github.io/shitjournal-backup/**

页面会从 `backup/index.json` 读取索引并列出新闻与预印本，点击条目可跳转到仓库内对应 Markdown 文件。

## 归档结构

条目按 **id 分目录** 存放：

- **新闻**：`backup/news/{slug 首字母}/{slug}.md`，如 `news/m/maintenance.md`
- **预印本**：`backup/preprints/{UUID 前 2 位}/{uuid}.md`，如 `preprints/1f/1fd278a6-7895-4c19-9d4e-5fdbb76904a7.md`
- **索引**：`backup/index.json` 记录当次同步的 URL、slug、标题与时间戳。

```
backup/
├── index.json
├── news/
│   ├── g/
│   ├── m/
│   └── z/
└── preprints/
    ├── 1f/
    ├── a9/
    └── ...
```

## 同步与触发

- **定时**：每日 UTC 00:00（北京时间 08:00）自动执行一次同步。
- **推送触发**：向 `main` 分支 push 时也会触发同步。
- **手动**：在 GitHub Actions 中选择 “ShitJournal Archive Sync” → “Run workflow” 可立即执行。

同步完成后，若有新增或变更，将自动提交并推送到本仓库。

## 本地同步

需在本地更新归档时：

```bash
pip install -r requirements.txt
playwright install chromium

# 仅同步新闻
python crawler.py crawl --news-only

# 同步新闻与预印本（可加 --preprints-limit N 限制预印本数量）
python crawler.py crawl
```

## 许可与免责

本归档仅供学术与个人备份之用。内容版权归 S.H.I.T Journal 及原作者所有；若来源站要求停止同步，将立即停止并配合处理。

完整需求与规格见 [`docs/REQUIREMENTS.md`](docs/REQUIREMENTS.md)。
