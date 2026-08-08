# Arca

[English](README.md) | [简体中文](README.zh-CN.md)

一个为人和 Agent 设计的、可随文件夹一起带走的文献库。文件夹就是数据库，
CLI 只是一个参考客户端。

<p align="center">
  <a href="https://x66ccff.github.io/arca/">
    <img src="assets/arca-demo.gif" width="960" alt="Arca 使用二十篇真实机器学习论文生成交互式关系图">
  </a>
</p>

<p align="center">
  <strong><a href="https://x66ccff.github.io/arca/">打开交互式 Demo →</a></strong>
</p>

## 快速开始

```bash
git clone https://github.com/x66ccff/arca.git
cd arca

./arca init library
./arca --library library add 1706.03762
./arca --library library search "attention" --jsonl
./arca --library library star 1706.03762
./arca --library library citation-sync
./arca --library library visualize
```

用任意浏览器打开 `library/_index/paper-graph.html`。生成的关系图是一个可以
离线使用的独立 HTML 文件。

`add` 默认下载 arXiv 元数据和 PDF。只需要元数据时使用 `--no-pdf`。

## 功能

- 用普通文件夹保存元数据、PDF、笔记、标注和论文关系。
- 通过 arXiv ID 或 URL 直接导入论文。
- 支持稳定的文本、JSON 和 JSONL 本地查询输出。
- 保存可移植的星标，以及经过人工审核、最长 30 字符的精简注记。
- 连接不同论文，形成可移植、可编辑的知识图谱。
- 生成包含引用关系和标题/摘要相似关系的交互式关系图。
- 显示引用同步覆盖情况，并在本地服务模式提供一键刷新。
- 使用原子写入、PDF 校验，并将删除的内容移动到 `.trash/`。

不需要数据库、服务器、账号或包管理器。本地搜索、笔记、图导出和可视化均可
离线运行；只有 arXiv 导入和 `citation-sync` 需要网络。只有附带的 CLI 需要
Python 3.9+；任何语言都可以直接读写规范中的 JSON、JSONL、Markdown 和 PDF。

## 示例命令

```bash
# 查询
./arca --library library list
./arca --library library get 1706.03762 --json
./arca --library library search "transformer" --jsonl
./arca --library library path 1706.03762

# 整理
./arca --library library update 1706.03762 --status key --add-tag attention
./arca --library library star 1706.03762
./arca --library library remark 1706.03762 --text "注意力架构的核心基线"
./arca --library library list --starred
./arca --library library note 1706.03762 "Canonical Transformer paper."
./arca --library library annotate 1706.03762 --page 3 --quote "..." --comment "Core architecture"

# 连接论文
./arca --library library link 1810.04805 extends 1706.03762 --note "Bidirectional pre-training"
./arca --library library neighbors 1706.03762 --depth 2 --json
./arca --library library graph --format dot

# 可视化与校验
./arca --library library citation-sync
./arca --library library visualize --center 1706.03762 --depth 2
./arca --library library doctor --full

# 可恢复删除
./arca --library library remove 1706.03762 --yes
./arca --library library restore 1706.03762
```

运行 `./arca --help` 或 `./arca COMMAND --help` 查看完整命令说明。

## 示例文献库

`examples/demo-library/` 包含 20 篇真实经典机器学习论文的元数据，覆盖
Word2Vec、GAN、ResNet、PPO、Transformer、BERT、DDPM、ViT 和 CLIP 等工作。
示例库不包含 PDF。

无需安装即可[打开在线交互图谱](https://x66ccff.github.io/arca/)，也可以用下面的
命令在本地生成相同的独立页面：

```bash
./arca --library examples/demo-library list
./arca --library examples/demo-library search "residual" --jsonl
./arca --library examples/demo-library citation-sync
./arca --library examples/demo-library visualize /tmp/arca-demo.html --force
```

## 文件夹格式

```text
library/
├── manifest.json
├── papers/<arxiv-id>/
│   ├── metadata.json
│   ├── paper.pdf
│   └── notes/
│       ├── summary.md
│       └── annotations.jsonl
├── graph/edges.jsonl
├── _index/                 # 生成内容，可安全重建
├── .staging/               # 事务式导入暂存区
└── .trash/                 # 可恢复删除
```

规范数据位于 `papers/`、`graph/` 和存储的文件中。`_index/` 只包含可重新生成的
索引与可视化状态。语言无关的文件格式详见 [SPEC.md](SPEC.md) 和
[`schema/`](schema/) 中的 JSON Schema。

## 可视化

带方向的实线表示由免费 Semantic Scholar API 获取的引用关系。较弱的虚线由
标题和摘要在本地计算得出。节点越大表示被引次数越多，越新的论文越不透明。
横向年份力场会把旧论文拉向左侧、新论文拉向右侧，同时保留引用与主题聚类力。
缩放时会逐步显示更多标签，点击节点可以突出其相邻论文。完成 `citation-sync`
后，可视化本身不需要联网。

星标论文会显示克制的金色微光，并优先出现在概览标签中；经过审核的精简注记会
显示在悬浮提示和选中面板里。页面顶部还会显示缓存新鲜度、已解析论文覆盖率和
库内引用边数量。

通过 `file://` 打开的独立页面仍会显示同步状态，但静态 HTML 无法执行本机命令，
因此同步按钮会被禁用。启动可选的本机回环服务后，即可一键调用 Semantic Scholar：

```bash
./arca --library library serve --open
```

该服务只绑定 `127.0.0.1`，仅提供生成的图谱和同步 API，不会暴露 PDF、笔记或
规范元数据。写操作需要每个进程独立的同源令牌，并校验回环 Host 和 Origin。

`remark` 每次设置或清空时都会在终端显示待写文本和字符数，审核者必须输入
`确认`；不存在非交互式跳过审核的参数。

## 许可证

MIT。附带的 D3 使用其自身许可证。示例库只再分发论文元数据，不包含 PDF。
