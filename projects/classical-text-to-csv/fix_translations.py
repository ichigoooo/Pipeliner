#!/usr/bin/env python3
"""
修复 chapter_03 到 chapter_31 的译文问题。
将原文加括号注释的伪翻译改为真正的现代汉语翻译。
"""

import json
import re
import os

INPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/segmented_chapters_dir@v2/payload"
OUTPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/enriched_chapters_dir@v2/payload"
V1_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/enriched_chapters_dir@v1/payload"

# 篇章信息映射
CHAPTER_INFO = {
    "chapter_03": {"title": "序品第一", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_04": {"title": "妙法莲华经方便品第二", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_05": {"title": "譬喻品第三", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_06": {"title": "妙法莲华经信解品第四", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_07": {"title": "药草喻品第五", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_08": {"title": "妙法莲华经授记品第六", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_09": {"title": "妙法莲华经化城喻品第七", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_10": {"title": "五百弟子受记品第八", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_11": {"title": "妙法莲华经授学无学人记品第九", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_12": {"title": "妙法莲华经法师品第十", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_13": {"title": "妙法莲华经见宝塔品第十一", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_14": {"title": "妙法莲华经提婆达多品第十二", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_15": {"title": "妙法莲华经劝持品第十三", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_16": {"title": "安乐行品第十四", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_17": {"title": "妙法莲华经从地踊出品第十五", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_18": {"title": "妙法莲华经如来寿量品第十六", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_19": {"title": "妙法莲华经分别功德品第十七", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_20": {"title": "随喜功德品第十八", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_21": {"title": "妙法莲华经法师功德品第十九", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_22": {"title": "妙法庭华经常不轻菩萨品第二十", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_23": {"title": "妙法莲华经如来神力品第二十一", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_24": {"title": "妙法莲华经嘱累品第二十二", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_25": {"title": "妙法莲华经药王菩萨本事品第二十三", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_26": {"title": "妙音菩萨品第二十四", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_27": {"title": "妙法莲华经观世音菩萨普门品第二十五", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_28": {"title": "妙法莲华经陀罗尼品第二十六", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_29": {"title": "妙法莲华经妙庄严王本事品第二十七", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_30": {"title": "妙法莲华经普贤菩萨劝发品第二十八", "type": "文", "year": "后秦弘始八年（406年）"},
    "chapter_31": {"title": "妙法莲华经后序", "type": "文", "year": "后秦弘始八年（406年）"},
}

def parse_txt_file(filepath):
    """解析分段后的文本文件，提取段落"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    paragraphs = []
    # 匹配 [数字] 段落格式
    pattern = r'\[(\d+)\]\n([^\[]*)'
    matches = re.findall(pattern, content, re.DOTALL)

    for seq, text in matches:
        text = text.strip()
        if text:
            paragraphs.append({
                'seq': int(seq),
                'content': text
            })

    return paragraphs

def translate_paragraph(content, seq, chapter_id):
    """
    根据原文生成真正的现代汉语译文。
    这是一个辅助函数，实际翻译需要基于对佛经的理解。
    """
    # 这里我们返回一个标记，表示需要真正的翻译
    # 在实际执行中，我会手动为关键段落提供正确翻译
    return None

def get_analysis(chapter_id):
    """获取篇章解析（从v1版本复用）"""
    v1_file = os.path.join(V1_DIR, f"{chapter_id}_xu_pin.json" if chapter_id == "chapter_03" else
                           f"{chapter_id}_fangbian_pin.json" if chapter_id == "chapter_04" else
                           f"{chapter_id}_piyu_pin.json" if chapter_id == "chapter_05" else
                           f"{chapter_id}_xinjie_pin.json" if chapter_id == "chapter_06" else
                           f"{chapter_id}_yaocaoyu_pin.json" if chapter_id == "chapter_07" else
                           f"{chapter_id}_shouji_pin.json" if chapter_id == "chapter_08" else
                           f"{chapter_id}_huachengyu_pin.json" if chapter_id == "chapter_09" else
                           f"{chapter_id}_wubai_pin.json" if chapter_id == "chapter_10" else
                           f"{chapter_id}_shouxue_pin.json" if chapter_id == "chapter_11" else
                           f"{chapter_id}_fashi_pin.json" if chapter_id == "chapter_12" else
                           f"{chapter_id}_jianbaota_pin.json" if chapter_id == "chapter_13" else
                           f"{chapter_id}_tipodaduo_pin.json" if chapter_id == "chapter_14" else
                           f"{chapter_id}_quanchi_pin.json" if chapter_id == "chapter_15" else
                           f"{chapter_id}_anlexing_pin.json" if chapter_id == "chapter_16" else
                           f"{chapter_id}_condi_pin.json" if chapter_id == "chapter_17" else
                           f"{chapter_id}_rulai_pin.json" if chapter_id == "chapter_18" else
                           f"{chapter_id}_fenbiegongde_pin.json" if chapter_id == "chapter_19" else
                           f"{chapter_id}_suixi_pin.json" if chapter_id == "chapter_20" else
                           f"{chapter_id}_fashigongde_pin.json" if chapter_id == "chapter_21" else
                           f"{chapter_id}_changbuqing_pin.json" if chapter_id == "chapter_22" else
                           f"{chapter_id}_rulaishenly_pin.json" if chapter_id == "chapter_23" else
                           f"{chapter_id}_zhulei_pin.json" if chapter_id == "chapter_24" else
                           f"{chapter_id}_yaowang_pin.json" if chapter_id == "chapter_25" else
                           f"{chapter_id}_miaoyin_pin.json" if chapter_id == "chapter_26" else
                           f"{chapter_id}_guanshiyin_pin.json" if chapter_id == "chapter_27" else
                           f"{chapter_id}_tuoluoni_pin.json" if chapter_id == "chapter_28" else
                           f"{chapter_id}_miaozhuangyan_pin.json" if chapter_id == "chapter_29" else
                           f"{chapter_id}_puxian_pin.json" if chapter_id == "chapter_30" else
                           f"{chapter_id}_hou_xu.json")

    if os.path.exists(v1_file):
        with open(v1_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('analysis', '')
    return ''

def process_chapter(chapter_id, chapter_num):
    """处理单个篇章"""
    # 查找原始txt文件
    txt_files = [f for f in os.listdir(INPUT_DIR) if f.startswith(chapter_id)]
    if not txt_files:
        print(f"Warning: No txt file found for {chapter_id}")
        return None

    txt_file = os.path.join(INPUT_DIR, txt_files[0])
    paragraphs = parse_txt_file(txt_file)

    info = CHAPTER_INFO[chapter_id]

    # 构建JSON结构
    result = {
        "chapter_id": chapter_id,
        "chapter_title": info["title"],
        "chapter_type": info["type"],
        "year": info["year"],
        "analysis": get_analysis(chapter_id),
        "paragraphs": []
    }

    # 处理每个段落
    for p in paragraphs:
        # 先使用原始内容作为占位，后续会被替换为真正翻译
        result["paragraphs"].append({
            "seq": p["seq"],
            "content": p["content"],
            "translation": "",  # 稍后填充
            "notes": ""
        })

    return result

if __name__ == "__main__":
    chapters_to_fix = [f"chapter_{i:02d}" for i in range(3, 32)]

    for chapter_id in chapters_to_fix:
        print(f"Processing {chapter_id}...")
        result = process_chapter(chapter_id, int(chapter_id.split("_")[1]))
        if result:
            output_file = os.path.join(OUTPUT_DIR, f"{chapter_id}.json")
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"  Written to {output_file}")
