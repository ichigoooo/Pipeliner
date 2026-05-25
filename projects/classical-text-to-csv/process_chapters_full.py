#!/usr/bin/env python3
"""
法华经篇章元数据丰富处理器 - 生成完整译文
"""

import os
import json
import re

INPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/segmented_chapters_dir@v2/payload"
OUTPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/enriched_chapters_dir@v8/payload"


def parse_chapter_file(filepath):
    """解析篇章文件，提取段落"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'\[(\d+)\]\n'
    parts = re.split(pattern, content)
    paragraphs = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            seq = int(parts[i])
            para_content = parts[i + 1].strip()
            if para_content:
                paragraphs.append({'seq': seq, 'content': para_content})
    return paragraphs


def translate_chapter_01(paragraphs):
    """御制大乘妙法莲华经序 - 译文"""
    translations = {
        1: "妙法莲华经，由后秦时期龟兹国三藏法师鸠摩罗什奉皇帝诏令翻译。御制《大乘妙法莲华经》序。",
        2: "昔日如来在耆阇崛山中，与大阿罗汉阿若憍陈如、摩诃迦叶等无量大众，演说大乘真经，名为《无量义》。当时天降宝花遍布充满，智慧之光显现祥瑞，照彻幽暗与显明之处，一切佛国世界六种震动，一切人天众生获得前所未有的体验，都欢喜赞叹，认为此经是诸佛如来秘密之藏，神妙难测，广大难以名状，能够拔救沉溺于深流中的众生，拯救迷失本性的昏迷者，功德弘远不可限量。追溯其源头，起始于印度，流传至中国，从西晋沙门竺法护开始翻译，名为《正法华》；到东晋龟兹三藏法师鸠摩罗什重新翻译，名为《妙法莲华》；至隋代天竺沙门阇那笈多所翻译的，亦名《妙法》。虽然三部经文义理重复互陈，但唯有三藏法师鸠摩罗什独得经旨。因历时久远，不免有讹误，若不加以校正，渐致多疑，因此特加校对，并命人雕版印刷以广流传。",
        3: "呜呼！如来怜悯诸众生有种种心性、种种欲望、种种行为、种种忆想分别，历劫缠绕无有出期，乃为此大事因缘现世，敷演畅达妙旨，作殊胜方便，使众生皆得度脱超登正觉，此实在是渡海之桥梁而照幽之智慧火炬。善男子、善女人，一切众生，能秉心至诚持诵佩服顶礼供养，即离一切苦恼，除一切业障，解一切生死之厄。不啻如饥饿之得食，如口渴之得饮，如寒冷之得火，如炎热之得凉，如贫穷之得宝，如疾病之得医，如子之得母，如渡海之得舟，其快适欣慰，有不可言者。噫！",
        4: "道非经无以寄托，法非经无以传承。依经以求法，依法以悟道，方识此经之旨清净微妙第一希有。遵行此经者则身臻康泰，诸种善根圆满具足，如莲华出水不染淤泥，即得五蕴皆空、六根清净，迅速跻身上善以成就正觉不难。若沉迷胶固，甘心堕落绝灭善根，则身罹苦趣，轮回于生死之域，其有尽极吗？虽然善恶两途由人所趋，为善获吉，为恶获凶，幽明果报不差锱铢。",
        5: "观此经者，当警戒！当勉励！",
        6: "永乐十八年四月十七日"
    }
    notes = {
        2: "耆阇崛山:灵鹫山,佛陀说法圣地。竺法护:西晋译经高僧。鸠摩罗什:后秦著名译经师。阇那笈多:隋代译经高僧。",
        3: "大事因缘:指佛陀出世度化众生的根本目的。正觉:佛果,无上正等正觉。",
        4: "五蕴:色、受、想、行、识五种聚合。六根:眼、耳、鼻、舌、身、意六种感官。",
        6: "永乐十八年:公元1420年,明成祖朱棣年号。"
    }
    result = []
    for p in paragraphs:
        seq = p['seq']
        result.append({
            "seq": seq,
            "content": p['content'],
            "translation": translations.get(seq, ""),
            "notes": notes.get(seq, "")
        })
    return result


def translate_chapter_02(paragraphs):
    """妙法莲华经弘传序 - 译文"""
    translations = {
        1: "《妙法莲华经》弘传序，唐代终南山释道宣撰述。",
        2: "《妙法莲华经》者，统摄诸佛降灵世间的本旨。蕴蓄结集于印度，出世已逾千年。东传中国，三百余载。西晋惠帝永康年间，长安青门炖煌菩萨竺法护，初翻此经，名《正法华》。东晋安帝隆安年间，后秦弘始年间，龟兹沙门鸠摩罗什再次翻译此经，名《妙法莲华》。",
        3: "隋代仁寿年间，大兴善寺北天竺沙门阇那笈多后来所翻译者，同名《妙法》。三经重复，文旨互陈。当时所宗尚者，皆弘扬秦本（鸠摩罗什译本）。其余支品、别偈，亦有其流传，具如序历所述，故不赘述。夫以灵岳降灵，非大圣无由开化；适化所及，非昔缘无以导心。",
        4: "所以仙苑告成，机缘分大小之别；金河嘱命，道殊半满之科。岂非教化被覆乘时之机，无足核其高会。是知五千退席，为进增慢之俦；五百授记，俱崇密化之迹。所以放光现瑞，开发请法之教源；出定扬德，畅演佛慧之宏略。朽宅通入大之文轨，化城引昔缘之不坠，系珠明理性之常在，凿井显示悟之多方。",
        5: "词义宛然，喻陈惟远。自非大哀旷济，拔救滞溺之沈流；一极悲心，拯济昏迷之失性。自汉至唐六百余载，总历群籍四千余轴，受持盛者无出此经。将非机教相扣，并智胜之遗尘；闻而深敬，俱威王之余绩。辄于经首，序而综述之。",
        6: "庶得早净六根，仰慈尊之嘉会；速成四德，趣乐土之玄猷。弘赞莫穷，永贻诸后。云尔。",
        7: "《妙法莲华经》卷第一，后秦龟兹国三藏法师鸠摩罗什奉诏翻译。"
    }
    notes = {
        2: "道宣:唐代高僧,律宗创始人。永康:西晋惠帝年号。隆安:东晋安帝年号。弘始:后秦姚兴年号。",
        3: "仁寿:隋文帝年号。阇那笈多:北天竺僧人,隋代译经家。",
        4: "五千退席:指《法华经》中五千增慢者离席。五百授记:指佛陀为五百弟子授成佛记。",
        5: "四德:指常乐我净四种功德。"
    }
    result = []
    for p in paragraphs:
        seq = p['seq']
        result.append({
            "seq": seq,
            "content": p['content'],
            "translation": translations.get(seq, ""),
            "notes": notes.get(seq, "")
        })
    return result


def translate_chapter_31(paragraphs):
    """妙法莲华经后序 - 译文"""
    translations = {
        1: "《妙法莲华经》后序，僧睿述。法师鸠摩罗什，长安人也。",
        2: "此经是诸佛之秘藏，众经之实体。其旨意深远，文辞巧妙，非一言可尽。"
    }
    result = []
    for p in paragraphs:
        seq = p['seq']
        result.append({
            "seq": seq,
            "content": p['content'],
            "translation": translations.get(seq, f"[段落{seq}内容待译]"),
            "notes": ""
        })
    return result


def process_chapter(filename, chapter_id, chapter_title, chapter_type, year, analysis):
    """处理单个篇章"""
    input_path = os.path.join(INPUT_DIR, filename)
    output_path = os.path.join(OUTPUT_DIR, filename.replace('.txt', '.json'))

    paragraphs = parse_chapter_file(input_path)

    # 根据篇章ID选择对应的翻译函数
    if filename == "chapter_01_yuzhi_xu.txt":
        enriched_paragraphs = translate_chapter_01(paragraphs)
    elif filename == "chapter_02_hongchuan_xu.txt":
        enriched_paragraphs = translate_chapter_02(paragraphs)
    elif filename == "chapter_31_hou_xu.txt":
        enriched_paragraphs = translate_chapter_31(paragraphs)
    else:
        # 其他篇章需要生成译文
        enriched_paragraphs = []
        for p in paragraphs:
            enriched_paragraphs.append({
                "seq": p['seq'],
                "content": p['content'],
                "translation": "",
                "notes": ""
            })

    output = {
        "chapter_id": chapter_id,
        "chapter_title": chapter_title,
        "chapter_type": chapter_type,
        "year": year,
        "analysis": analysis,
        "paragraphs": enriched_paragraphs
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return len(enriched_paragraphs)


if __name__ == "__main__":
    # 这里需要填入完整的CHAPTER_INFO和处理逻辑
    print("Script created - need to add full chapter data")
