#!/usr/bin/env python3
"""
修复 chapter_03_translation.json 中的引号问题
"""

import json
import re

# 读取文件
with open('/Users/wuyuheng/Documents/Projects/Pipeliner/projects/classical-text-to-csv/chapter_03_translation.json', 'r', encoding='utf-8') as f:
    content = f.read()

# 步骤1: 保护 JSON 结构中的引号（临时替换）
content = content.replace('\"translation\":', '@@TRANSLATION@@:')
content = content.replace('\"notes\":', '@@NOTES@@:')
content = content.replace('\"seq\":', '@@SEQ@@:')
content = content.replace('\"content\":', '@@CONTENT@@:')
content = content.replace('\"paragraphs\":', '@@PARAGRAPHS@@:')

# 步骤2: 将中文引号替换为单引号
content = content.replace('"', "'")
content = content.replace('"', "'")
content = content.replace('「', "'")
content = content.replace('」', "'")

# 步骤3: 恢复 JSON 结构
content = content.replace('@@TRANSLATION@@:', '"translation":')
content = content.replace('@@NOTES@@:', '"notes":')
content = content.replace('@@SEQ@@:', '"seq":')
content = content.replace('@@CONTENT@@:', '"content":')
content = content.replace('@@PARAGRAPHS@@:', '"paragraphs":')

# 步骤4: 确保最外层是双引号
if content.startswith("'"):
    content = content.replace("'", '"', 1)
if content.endswith("'"):
    content = content[:-1] + '"'

# 现在解析 JSON
try:
    data = json.loads(content)
    print(f"Successfully parsed JSON with {len(data['paragraphs'])} paragraphs")

    # 写回文件
    with open('/Users/wuyuheng/Documents/Projects/Pipeliner/projects/classical-text-to-csv/chapter_03_translation.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("Fixed and saved chapter_03_translation.json")
except json.JSONDecodeError as e:
    print(f"JSON error: {e}")
    # 找到错误位置
    lineno = e.lineno
    colno = e.colno
    lines = content.split('\n')
    if lineno <= len(lines):
        print(f"Error at line {lineno}, column {colno}:")
        print(lines[lineno-1][:100])
        print(" " * min(colno-1, 80) + "^")
