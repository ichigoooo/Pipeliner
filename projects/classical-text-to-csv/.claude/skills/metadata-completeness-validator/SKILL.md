---
name: metadata-completeness-validator
description: 节点 chapter_metadata_enrichment 的 validator skill（validator_id=metadata-completeness-check）。验证所有篇章的元数据字段完整性，确保没有遗漏处理的篇章。
---

# Node Validator Skill

- node_id: chapter_metadata_enrichment
- role: validator
- validator_id: metadata-completeness-check

## 验证目标

确保所有篇章文档都已完成元数据丰富处理，且所有必填字段均已填写。

## 检查项目

### 1. 覆盖率检查

- enriched_chapters_dir 中的篇章数量与 segmented_chapters_dir 中的篇章数量一致
- 不允许有遗漏未处理的篇章文档

### 2. 必填字段完整性

对每个篇章检查以下字段：

| 字段 | 要求 |
|------|------|
| chapter_id | 必填，唯一 |
| chapter_title | 必填，非空 |
| chapter_type | 必填，为诗/词/文/赋/论之一 |
| analysis | 必填，非空，非占位文本，至少 50 字 |
| paragraphs | 必填，至少有 1 个段落 |
| paragraphs[].seq | 必填，从 1 开始连续递增 |
| paragraphs[].content | 必填，非空 |
| paragraphs[].translation | 诗词类必填；散文类若无翻译必要可为空，但不得为占位文本 |

### 3. 段落序号连续性

每个篇章内的段落 seq 字段必须从 1 开始，连续递增，无跳号，无重复。

### 4. metadata_enrichment_manifest 检查

清单文件必须记录：
- 总篇章数
- 每个篇章的处理状态
- 处理时间戳

## 通过标准

所有篇章均已处理，所有必填字段已填写，无任何占位文本，段落序号连续正确。

## 输出格式

```json
{
  "verdict": "pass|fail",
  "total_chapters": 10,
  "processed_chapters": 10,
  "issues": ["具体问题描述"],
  "summary": "验证结果摘要"
}
```

参考资料：
- references/node_context.json
