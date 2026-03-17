---
name: text-chunking
description: 节点 text_chunking 的 executor skill。
---

# Text Chunking Skill

## Description

将预处理后的全文切分为一组顺序文档，每个文档不超过 20000 字。

## Purpose

在结构识别前先降低单次输入体量，避免大模型直接处理整本书而长时间无输出。

## Output

- `text_chunks_dir`：顺序切块文档目录
- `chunk_manifest`：切块清单，记录每个切块的字符范围、长度和文件名

## Guidelines

1. 必须保持全文顺序，不允许遗漏或重复任何内容。
2. 每个切块文档长度必须不超过 20000 字。
3. 优先沿自然段、空行、标题行或其他明显边界切开，减少跨结构截断。
4. 如果无法恰好在自然边界切开，可选择最接近上限的位置，但仍要保证不超过 20000 字。
5. `chunk_manifest` 必须能帮助后续节点把局部线索映射回全书位置。
