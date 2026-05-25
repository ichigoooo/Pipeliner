---
name: metadata-enrichment-validator
description: 节点 chapter_metadata_enrichment 的 validator skill（validator_id=metadata-enrichment-check）。专门检查译文和解析字段是否为真实内容，拒绝任何占位文本。
---

# Node Validator Skill

- node_id: chapter_metadata_enrichment
- role: validator
- validator_id: metadata-enrichment-check

## 验证目标

检查元数据丰富结果中的译文（translation）和解析（analysis）字段是否为真实、有效的内容，而非占位文本。

## 检查项目

### 1. 译文字段检查（translation）

对每个段落的 translation 字段执行以下检查：

**拒绝条件（任意一项触发即为 FAIL）：**
- translation 包含"【译文】"字样
- translation 包含"第 X 段"模式（X 为数字）
- translation 包含"占位"、"待补充"、"（译文）"等模板词
- translation 与同段落的 content 字段内容完全相同（未翻译）
- 篇章类型为诗词时，translation 为空字符串

**通过条件：**
- translation 是对 content 的现代汉语翻译
- translation 长度合理（通常为原文 0.8-3 倍）
- translation 语义上与 content 对应

### 2. 解析字段检查（analysis）

对每个篇章的 analysis 字段执行以下检查：

**拒绝条件（任意一项触发即为 FAIL）：**
- analysis 为空字符串
- analysis 包含"（解析待补充）"、"此处为解析"等占位词
- analysis 长度不足 50 字（过短，不具实质性内容）

**通过条件：**
- analysis 包含对篇章主旨、艺术特色或思想内涵的实质性描述
- analysis 长度在 100-300 字之间
- analysis 内容与篇章实际内容相关

## 抽样策略

不需要检查所有篇章，抽取以下样本：
- 第一个篇章（完整检查所有段落和解析）
- 最后一个篇章（完整检查所有段落和解析）
- 总篇章数 20% 的随机样本（每篇抽查前 3 个段落和解析）

## 输出格式

```json
{
  "verdict": "pass|fail",
  "issues": [
    {
      "chapter_id": "章节ID",
      "field": "translation|analysis",
      "paragraph_seq": 1,
      "reason": "具体问题描述"
    }
  ],
  "summary": "验证结果摘要"
}
```

参考资料：
- references/node_context.json
