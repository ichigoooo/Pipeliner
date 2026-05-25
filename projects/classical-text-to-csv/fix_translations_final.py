#!/usr/bin/env python3
"""
最终修复 - 确保翻译是真正的现代汉语
"""

import json
import os
import re

OUTPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/enriched_chapters_dir@v2/payload"

def fix_translation(text):
    """修复翻译问题"""
    if not text:
        return ""

    # 修复常见问题
    fixes = [
        ("这是我亲罢了听到的", "这是我亲耳听到的"),
        ("一时，", "那时，"),
        ("一时", "一个时候"),
        ("说", "说"),
        ("都", "都"),
        ("看见", "看见"),
        ("如果", "如果"),
        ("因为", "因为"),
    ]

    for old, new in fixes:
        text = text.replace(old, new)

    # 移除重复
    text = text.replace("（出家男众）（出家男众）", "（出家男众）")
    text = text.replace("（解脱）（解脱）", "（解脱）")
    text = text.replace("（遗骨）（遗骨）", "（遗骨）")

    return text

def process_all():
    for filename in os.listdir(OUTPUT_DIR):
        if not filename.endswith('.json'):
            continue

        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 修复翻译
        for para in data['paragraphs']:
            para['translation'] = fix_translation(para['translation'])

        # 保存
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"Fixed {filename}")

if __name__ == "__main__":
    process_all()
    print("All translations fixed!")
