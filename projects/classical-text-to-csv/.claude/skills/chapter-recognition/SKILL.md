# Chapter Recognition Skill

## Description

自动识别古籍文本的篇章结构，从整部著作文本中划分出各个篇章（Chapter），并为每个篇章提取标题和类型信息。

## Purpose

对于输入的完整著作文本，自动识别其中的篇章边界，根据文本特征（如章节标题、分段标记、序号、空行等）将文本划分为多个篇章，并提取每个篇章的元数据。

## Input

- `preprocessed_text` (file, required): 预处理后的文本文件路径
- `structure_hint` (string, optional): 篇章结构提示，如"共5章"、"包含序、正文、跋"等

## Output

- `chapters_structure` (structured_data): 识别出的篇章结构列表，格式如下：
  ```json
  {
    "chapters": [
      {
        "chapter_title": "篇章标题",
        "chapter_category": "篇章类型（诗/词/文/赋/论）",
        "creation_year": 创作年份或null,
        "content_start": "内容起始位置标记",
        "content_end": "内容结束位置标记"
      }
    ]
  }
  ```

## Guidelines

1. **篇章识别依据**：
   - 明显的章节标题（如"第一章"、"卷一"、"序"、"跋"等）
   - 段落之间的空行或分隔符
   - 文本中的序号标记
   - 标题的格式特征（如居中、加粗等，如果原文有标记）

2. **篇章标题提取**：
   - 优先使用原文中的章节标题
   - 如果标题不明显，根据内容生成描述性标题
   - 确保标题唯一性（在同一著作内）

3. **篇章类型判断**：
   - 根据标题关键词判断（如诗、词、赋、论等）
   - 根据内容特征判断
   - 默认值为"文"

4. **特殊情况处理**：
   - 如果文本无明显篇章结构，将整个文本作为一个篇章处理
   - 识别序言、跋、附录等特殊篇章
   - 处理残缺的篇章标题

## Example

输入文本：
```
序

本文乃测试之作...

卷一 诗词选

第一首
内容...

第二首
内容...

卷二 散文选

第一篇
内容...
```

输出结构：
```json
{
  "chapters": [
    {
      "chapter_title": "序",
      "chapter_category": "文",
      "creation_year": null,
      "content_start": "本文乃测试之作...",
      "content_end": "..."
    },
    {
      "chapter_title": "卷一 诗词选",
      "chapter_category": "诗",
      "creation_year": null,
      "content_start": "第一首",
      "content_end": "..."
    },
    {
      "chapter_title": "卷二 散文选",
      "chapter_category": "文",
      "creation_year": null,
      "content_start": "第一篇",
      "content_end": "..."
    }
  ]
}
```
