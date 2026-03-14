# Chapter Structure Validator Skill

## Description

验证篇章结构识别结果的质量和完整性。

## Purpose

检查 `chapter-recognition` 节点的输出，确保篇章划分合理、无重叠、无遗漏，并且每个篇章都有有效的标题和类型信息。

## Input

- `chapters_structure` (structured_data, required): 篇章结构识别结果

## Output

- `validation_result` (structured_data): 验证结果，包含：
  - `status`: "PASS" 或 "FAIL"
  - `issues`: 问题列表（如有）
  - `metrics`: 验证指标

## Validation Rules

1. **完整性检查**：
   - 至少识别出一个篇章
   - 每个篇章都有 `chapter_title` 字段
   - 每个篇章都有 `chapter_category` 字段

2. **一致性检查**：
   - 篇章标题在同一著作内唯一（允许重复标题警告但不阻断）
   - 篇章类型必须是有效值：诗、词、文、赋、论 或英文 shi、ci、wen、fu、lun

3. **无重叠检查**：
   - 各篇章的内容范围不能重叠
   - 原文所有内容都应该被分配到某个篇章

4. **合理性检查**：
   - 每个篇章的内容不应该为空或过少（少于10个字符警告）
   - 篇章标题不应该为空或仅包含空白字符

## Example

输入：
```json
{
  "chapters": [
    {
      "chapter_title": "序",
      "chapter_category": "文",
      "creation_year": null
    }
  ]
}
```

输出：
```json
{
  "status": "PASS",
  "issues": [],
  "metrics": {
    "total_chapters": 1,
    "valid_chapters": 1,
    "warnings": 0
  }
}
```
