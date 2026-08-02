# Arca

[English](README.md) | [简体中文](README.zh-CN.md)

一个为人和 Agent 设计的、可随文件夹一起带走的文献库。文件夹就是数据库，
CLI 只是一个参考客户端。

<p align="center">
  <img src="assets/arca-demo.gif" width="960" alt="Arca 使用二十篇真实机器学习论文生成交互式关系图">
</p>

## 快速开始

```bash
git clone https://github.com/x66ccff/arca.git
cd arca

./arca init library
./arca --library library add 1706.03762
./arca --library library search "attention" --jsonl
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
- 连接不同论文，形成可移植、可编辑的知识图谱。
- 生成包含引用关系和标题/摘要相似关系的交互式关系图。
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
标题和摘要在本地计算得出。节点越大表示连接越多，越新的论文越不透明。缩放时
会逐步显示更多标签，点击节点可以突出其相邻论文。完成 `citation-sync` 后，
可视化本身不需要联网。

## 许可证

MIT。附带的 D3 使用其自身许可证。示例库只再分发论文元数据，不包含 PDF。
