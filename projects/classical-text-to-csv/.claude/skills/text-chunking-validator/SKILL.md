---
name: text-chunking-validator
description: 节点 text_chunking 的 validator skill（validator_id=text-chunking-check）。
---

# Text Chunking Validator Skill

## Description

校验全文切块结果是否足以支撑后续结构识别。

## Purpose

确保切块结果覆盖全文、顺序正确、每块长度受控，并且不会因为错误切块导致后续结构识别失真。

## Guidelines

1. 每个切块文档必须不超过 20000 字。
2. 切块之间不能重叠，也不能出现明显遗漏。
3. `chunk_manifest` 应与目录内文档一一对应，顺序和字符范围必须连续。
4. 如果切块结果明显破坏结构连续性或缺少关键元信息，应要求返工。
