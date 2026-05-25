#!/usr/bin/env python3
"""
法华经篇章元数据丰富处理器
"""

import os
import json
import re
from pathlib import Path

INPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/segmented_chapters_dir@v2/payload"
OUTPUT_DIR = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/enriched_chapters_dir@v8/payload"

# 篇章信息映射
CHAPTER_INFO = {
    "chapter_01_yuzhi_xu.txt": {
        "chapter_id": "chapter_01",
        "chapter_title": "御制大乘妙法莲华经序",
        "chapter_type": "序",
        "year": "明代",
        "analysis": "此篇为明成祖朱棣于永乐十八年（1420年）为《妙法莲华经》所撰写的御制序言。序文阐述了佛教经典东传中国的历史，从西晋竺法护初译《正法华》，到东晋鸠摩罗什重译《妙法莲华》，再到隋代阇那笈多所译版本，梳理了三部译本的传承脉络。朱棣以帝王之尊，强调此经"拔滞溺之沈流，拯昏迷之失性"的功德，劝勉善男子、善女人持诵顶礼，以离苦恼、除业障。序文辞藻典雅，体现了明代皇室对佛教的尊崇，以及帝王以佛法教化臣民的政治意图。"
    },
    "chapter_02_hongchuan_xu.txt": {
        "chapter_id": "chapter_02",
        "chapter_title": "妙法莲华经弘传序",
        "chapter_type": "序",
        "year": "唐代",
        "analysis": "此篇为唐代终南山释道宣所撰弘传序。道宣为佛教律宗大师，此序系统梳理了《法华经》的翻译史与弘传史。序文指出此经"统诸佛降灵之本致"，阐明其在大乘佛教中的核心地位。文中详述了西晋竺法护、后秦鸠摩罗什、隋代阇那笈多三次翻译的经过，并推崇鸠摩罗什译本为时人所宗尚。序文还概述了《法华经》的核心思想，如"五千退席""五百授记""放光现瑞"等重要典故，以及"朽宅""化城""系珠""凿井"等著名譬喻，为理解全经思想奠定了基础。"
    },
    "chapter_03_xu_pin.txt": {
        "chapter_id": "chapter_03",
        "chapter_title": "序品第一",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《序品》为《法华经》二十八品之首，是全经的总序。本品描绘了佛陀在王舍城耆阇崛山为大比丘众万二千人及八万菩萨摩诃萨等诸大弟子演说《无量义经》后的场景。佛陀入于无量义处三昧，眉间放白毫相光，照东方万八千世界，现诸佛说法、众生轮回等种种瑞相。弥勒菩萨见此异象生疑，请问文殊菩萨。文殊以过去曾见类似瑞相为答，暗示将有殊胜法门宣说。本品通过神通示现与会众云集的场景，奠定了全经"开权显实、会三归一"的主题基调，为后续佛陀出定宣说《法华》妙法做了充分铺垫。"
    },
    "chapter_04_fangbian_pin.txt": {
        "chapter_id": "chapter_04",
        "chapter_title": "妙法莲华经方便品第二",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《方便品》为《法华经》核心篇章之一，佛陀于此品正式开显一乘妙法。本品开篇佛陀自赞所得智慧甚深无量，唯佛与佛乃能究尽诸法实相。佛陀指出过去所说三乘教法皆是方便，为引导众生出离三界而设。舍利弗等声闻弟子闻所未闻，心生疑悔，佛陀以"止止不须说"欲止其问，后以偈颂重宣此义。本品提出"诸法实相"的十如是义：如是相、如是性、如是体、如是力、如是作、如是因、如是缘、如是果、如是报、如是本末究竟等，此为天台宗"十如是"思想的经典依据。"
    },
    "chapter_05_piyu_pin.txt": {
        "chapter_id": "chapter_05",
        "chapter_title": "譬喻品第三",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《譬喻品》承接《方便品》，舍利弗闻法欢喜，自述从前不解方便之说、自谓得涅槃的悔恨。本品以"三车喻"（羊车、鹿车、牛车喻三乘，大白牛车喻一乘）和"火宅喻"为全经最著名的譬喻。佛陀以长者诱引火宅中诸子出离，先许三车后赐大白牛车为喻，阐明三乘方便、一乘究竟之理。此喻生动形象地说明了佛陀宣说声闻、缘觉、菩萨三乘教法，皆为度脱众生出离三界火宅的方便，究竟目标是令众生成就佛果。此品是理解《法华经》"会三归一"思想的关键篇章。"
    },
    "chapter_06_xinjie_pin.txt": {
        "chapter_id": "chapter_06",
        "chapter_title": "妙法莲华经信解品第四",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《信解品》讲述摩诃迦叶、须菩提、摩诃迦旃延、摩诃目犍连四大声闻弟子，闻佛开显一乘妙法后，以"穷子喻"理解自身得度的因缘。四弟子以贫穷子归家不识其父、其父以方便渐诱其子为喻，说明自己昔于佛法中得小涅槃而自谓满足，不知如来慈悲深意。穷子喻生动描绘了声闻弟子从初闻大乘而生怖畏，到渐修渐证，最终领受家业的过程，体现了《法华经》"开权显实"的核心思想，也为声闻弟子回小向大、究竟成佛提供了理论依据。"
    },
    "chapter_07_yaocaoyu_pin.txt": {
        "chapter_id": "chapter_07",
        "chapter_title": "药草喻品第五",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《药草喻品》以"药草喻"阐明佛陀教法普润众生的道理。佛陀以天降大雨普润草木，一雨所润而诸药草大小各有生长为喻，说明如来以智慧慈悲普润一切众生，而众生随其根性、愿力、修为不同，所得利益亦有差异。此品破除了弟子们对"众生皆有佛性、同成佛道"的疑惑，阐明"三草二木"（小草喻人天乘、中草喻声闻缘觉、上草喻菩萨，小树大树喻不同位阶菩萨）虽然禀润不同，但皆蒙一雨之润。此喻体现了佛法平等而众生差别接受的道理，强调佛以一音演说法，众生随类各得解。"
    },
    "chapter_08_shouji_pin.txt": {
        "chapter_id": "chapter_08",
        "chapter_title": "妙法莲华经授记品第六",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《授记品》为四大声闻弟子授成佛之记。摩诃迦叶、须菩提、摩诃迦旃延、摩诃目犍连四大弟子闻法信解后，佛陀依次为四人授记未来成佛。摩诃迦叶当来世奉觐三百万亿诸佛，于光明世界中成佛，号曰光明如来；须菩提当来世奉觐三百万亿那由他佛，于名相世界中成佛，号曰名相如来；摩诃迦旃延当来世奉觐二万亿佛，于星宿世界中成佛，号曰阎浮那提金光如来；摩诃目犍连当来世奉觐二千恒沙佛，于意乐世界中成佛，号曰多摩罗跋栴檀香神通如来。本品正式印证了声闻弟子亦可成佛，体现了《法华经》"开权显实"的精神。"
    },
    "chapter_09_huachengyu_pin.txt": {
        "chapter_id": "chapter_09",
        "chapter_title": "妙法莲华经化城喻品第七",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《化城喻品》以"化城喻"阐明佛乘方便之理，并为过去世大通智胜佛时的十六王子（即现今释迦及弥勒等菩萨）授记。佛陀以导师引众宝处，于险道中化作城池令众生止息为喻，说明涅槃如化城，非是真实，只是佛陀为度脱众生而设的方便。本品详细叙述过去久远劫前大通智胜佛出世，十六王子闻法出家、请转法轮，并于八千亿劫中演说《法华经》的因缘。佛陀指出过去教化的弟子即是现今会中弟子，过去所行佛道即是今所行之道。本品体现了《法华经》"久远实成"的思想，为佛陀成佛久远、寿命无量做了铺垫。"
    },
    "chapter_10_wubai_pin.txt": {
        "chapter_id": "chapter_10",
        "chapter_title": "五百弟子受记品第八",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《五百弟子受记品》为富楼那弥多罗尼子等五百阿罗汉授成佛记。本品以"系珠喻"说明佛陀往昔于弟子心中种下佛种，而弟子不自知、自谓得涅槃，如今方识本心。富楼那为佛说法人中第一，曾于九十亿佛所护持助宣，佛陀为授记于贤劫中成佛，号法明如来。又五百阿罗汉、学无学八千人皆得授记，于未来世成佛。本品还记录了阿难、罗睺罗请求授记，佛陀预言阿难于供养六十二亿佛后，于安乐世界成佛，号山海慧自在通王如来；罗睺罗当来世奉觐十恒河沙佛后成佛，号蹈七宝华如来。"
    },
    "chapter_11_shouxue_pin.txt": {
        "chapter_id": "chapter_11",
        "chapter_title": "妙法莲华经授学无学人记品第九",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《授学无学人记品》为阿难、罗睺罗及学无学二千人授成佛记。阿难为多闻第一，常侍佛侧，持说法藏，佛陀为之授记：于供养六十二亿诸佛后，于安乐世界成佛，号山海慧自在通王如来，其世界庄严妙好，寿命无量。罗睺罗为佛陀之子、密行第一，授记于未来世成佛，号蹈七宝华如来，国名清净，寿命无量。学无学二千人亦皆授记，于未来世成佛。本品进一步印证了《法华经》"一切众生皆可成佛"的思想，无论在家出家、学无学人，只要发心修行，究竟皆成佛道。"
    },
    "chapter_12_fashi_pin.txt": {
        "chapter_id": "chapter_12",
        "chapter_title": "妙法莲华经法师品第十",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《法师品》阐述受持、读诵、解说、书写《法华经》的法师功德。本品定义"法师"为受持、读诵、解说、书写是经者，无论在家出家，皆得称法师。佛陀为药王菩萨、大乐说菩萨解说法师功德：若善男子、善女人于如来灭后，能于一日至五日中以种种供养具供养是经，其功德胜过供养诸佛舍利。又云若有人受持读诵是经，解其义趣，如说修行，当知是人行普贤行，于无量佛所深种善根。本品还提到法师应起慈心、大悲心、安乐心，对一切众生说此经典，并得诸佛菩萨护念加持。"
    },
    "chapter_13_jianbaota_pin.txt": {
        "chapter_id": "chapter_13",
        "chapter_title": "妙法莲华经见宝塔品第十一",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《见宝塔品》为《法华经》中极具戏剧性的篇章。多宝佛塔从地涌出，住虚空中，塔中出声赞叹释迦牟尼佛善说《法华经》。佛陀以右指开塔门，多宝佛分半座与释迦，二佛并坐一座。多宝佛在过去久远劫前成佛，发愿于十方世界有说《法华经》处，必往听受。本品通过多宝佛塔涌现、二佛并坐的神奇场景，印证了《法华经》的殊胜功德，也象征着久远实成佛与今成佛共同见证一乘妙法。本品还提到八岁龙女献珠成佛的典故，体现《法华经》"一切众生皆可成佛"的平等精神。"
    },
    "chapter_14_tipodaduo_pin.txt": {
        "chapter_id": "chapter_14",
        "chapter_title": "妙法莲华经提婆达多品第十二",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《提婆达多品》记述提婆达多与佛陀的宿世因缘，以及八岁龙女成佛的典故。提婆达多虽为佛陀堂弟，却常怀恶心、出佛身血、破和合僧，但佛陀指出过去世中提婆达多曾为仙人，为其宣说《法华经》，故今得成佛。本品说明即使是恶知识，只要与佛法结缘，亦可得度。又记述文殊师利在龙宫宣说《法华经》，娑竭罗龙王之女年始八岁，以龙珠献佛，即身成佛，转女成男，往南方无垢世界成佛。此段破除了"女身不能成佛""须经三大阿僧祇劫修行"等执著，彰显《法华经》顿教法门、平等成佛的思想。"
    },
    "chapter_15_quanchi_pin.txt": {
        "chapter_id": "chapter_15",
        "chapter_title": "妙法莲华经劝持品第十三",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《劝持品》为药王菩萨、大乐说菩萨及二万菩萨于佛前发愿，于佛灭后受持、读诵、演说、书写《法华经》。本品中，药王菩萨与二万菩萨各各发愿，于恶世中受持是经，不惜身命。佛陀赞叹诸菩萨的大愿，并说明末世持经之难：邪见众生会轻慢、诋毁、攻击受持《法华经》者，但菩萨应以忍辱心、慈悲心不与之计较。本品强调了末法时代弘扬《法华经》的殊胜功德与艰难险阻，劝勉菩萨弟子发大誓愿，于恶世中护持正法，体现了菩萨"难行能行、难忍能忍"的济世精神。"
    },
    "chapter_16_anlexing_pin.txt": {
        "chapter_id": "chapter_16",
        "chapter_title": "安乐行品第十四",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《安乐行品》文殊师利请问末世持经之法，佛陀开示四种安乐行：身安乐行、口安乐行、意安乐行、誓愿安乐行。身安乐行要求菩萨不亲近国王、大臣、外道梵志、邪见人等，住于中道，行处近处皆得安乐。口安乐行要求不说他人过恶、不轻慢他、不赞毁他。意安乐行要求修大慈悲心、修寂灭心、修无是非心。誓愿安乐行要求发愿于佛灭后受持是经，与诸众生起慈悲心。本品还提到菩萨应观一切法空、无相、无作，于诸深法心不惊怖，体现了《法华经》与般若中观思想的融合，为末世修行者提供了具体的行为准则。"
    },
    "chapter_17_condi_pin.txt": {
        "chapter_id": "chapter_17",
        "chapter_title": "妙法莲华经从地踊出品第十五",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《从地踊出品》描述六万恒沙等菩萨摩诃萨从地涌出，为释迦牟尼佛弟子，表示在娑婆世界诵习《法华经》。弥勒菩萨疑惑这些菩萨从何而来，释迦牟尼佛指示由文殊菩萨等可见此土下方有世界名莲华藏，有佛名净华宿王智如来，是诸菩萨于彼佛所发菩提心、修行此经。本品揭示了娑婆世界下方无量世界，以及释迦牟尼佛在此土成佛久远、度生无量的事实，为下文《如来寿量品》开显佛寿无量、久远实成作了铺垫。本品体现了《法华经》的空间观——华藏世界海重重无尽，以及佛陀救度众生的广大悲愿。"
    },
    "chapter_18_rulai_pin.txt": {
        "chapter_id": "chapter_18",
        "chapter_title": "妙法莲华经如来寿量品第十六",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《如来寿量品》为《法华经》核心篇章，开显佛陀寿命无量、久远实成的甚深秘密。本品指出诸佛如来方便示现涅槃，实非真灭，释迦牟尼佛成佛以来已历无量无边百千万亿那由他劫，为度众生方便示现生老病死。佛陀以良医为喻：父（佛）先以常在与子（众生）药，子不服而父远游；父归后方便诈死，令子醒悟服药。此喻说明佛陀示现涅槃是令众生珍惜佛法、精进修行。本品揭示佛身常住不灭，灭度只是度生方便的示现，体现了《法华经》最高的法身常住思想，为全经理论核心。"
    },
    "chapter_19_fenbiegongde_pin.txt": {
        "chapter_id": "chapter_19",
        "chapter_title": "妙法莲华经分别功德品第十七",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《分别功德品》阐述听闻《如来寿量品》所得功德。本品分两部分：一是闻法功德，若有善男子、善女人闻佛寿长远，乃至生一念信解，所得功德无量无边，胜过布施恒河沙佛。二是随喜功德，若有人于如来灭后，闻是经不惊不怖、随喜功德，其功德亦不可思议。本品还提到五品法师位：随喜闻法、受持读诵、为人解说、兼行六度、正行六度，为天台宗"五品弟子位"的理论来源。佛陀指出随喜《法华经》功德胜过供养无数诸佛，劝勉众生于此经起深信解。"
    },
    "chapter_20_suixi_pin.txt": {
        "chapter_id": "chapter_20",
        "chapter_title": "随喜功德品第十八",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《随喜功德品》专述随喜《法华经》的功德。弥勒菩萨请问随喜功德，佛陀以譬喻说明：若有人于法师说法时随喜，其功德胜过有人以恒河沙等七宝布施众生，又令众生得阿罗汉果，乃至令众生得辟支佛果。又胜过有人以七宝满三千大千世界供养佛塔。本品通过层层递进的比较，彰显随喜《法华经》的殊胜功德。随喜者因一念信解，与法相应，即得无量福德，体现了《法华经》信愿行的重要性，以及一念随喜即与佛智相应的圆顿法门特色。"
    },
    "chapter_21_fashigongde_pin.txt": {
        "chapter_id": "chapter_21",
        "chapter_title": "妙法莲华经法师功德品第十九",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《法师功德品》详细描述受持《法华经》所得六根清净功德。本品说明若善男子、善女人受持是经，若读、若诵、若解说、若书写，得千二百眼功德、千二百耳功德、千二百鼻功德、千二百舌功德、千二百身功德、千二百意功德。眼能见三千大千世界内外所有，耳能闻十方说法声音，鼻能嗅诸香而知其来源，舌能演说深法、出清净妙音，身能显现清净色身、为众生所乐见，意能通达诸深法义。本品以六根清净彰显受持《法华经》的殊胜果报，体现了此法门的圆满功德。"
    },
    "chapter_22_changbuqing_pin.txt": {
        "chapter_id": "chapter_22",
        "chapter_title": "妙法莲华经常不轻菩萨品第二十",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《常不轻菩萨品》记述过去威王佛时，常不轻菩萨以忍辱行弘扬《法华经》的因缘。常不轻菩萨不专读诵经典，但行礼拜，见四众皆赞言："我不敢轻于汝等，汝等皆当作佛。"因轻慢四众而遭打骂侮辱，但忍辱不惊，命终时得闻《法华经》六根清净，广为人说。本品说明常不轻菩萨即是释迦牟尼佛的过去身，以此因缘成佛。本品强调"一切众生皆可成佛"的甚深信心，以及忍辱波罗蜜的重要性，为末世修行者树立了光辉榜样，体现了《法华经》众生佛性平等的究竟义。"
    },
    "chapter_23_rulaishenly_pin.txt": {
        "chapter_id": "chapter_23",
        "chapter_title": "妙法莲华经如来神力品第二十一",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《如来神力品》描述释迦牟尼佛及十方诸佛现大神力，护持《法华经》。本品中，佛陀从三昧起，以种种神通力加持此经，使之一切世间无能破坏。又十方无量诸佛各各现大神力，护持是经，令未来世菩萨摩诃萨得如来智慧。本品显示《法华经》为诸佛秘密之藏、神妙叵测，故以大神力加持护持。佛陀并将此经付嘱菩萨摩诃萨，令于末世弘扬流通。本品体现了《法华经》在佛教经典中的特殊地位，以及诸佛对此经的重视与护持。"
    },
    "chapter_24_zhulei_pin.txt": {
        "chapter_id": "chapter_24",
        "chapter_title": "妙法莲华经嘱累品第二十二",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《嘱累品》为释迦牟尼佛以《法华经》殷勤付嘱菩萨摩诃萨。本品简短而意义重大，佛陀从法座起，以右手摩无量菩萨摩诃萨顶，嘱累此经，令于十方世界流布此法，勿令断绝。又言若有众生不信受者，当于如来余深法中示教利喜。本品体现了佛陀对《法华经》传承的重视，以及菩萨弘法利生的责任。"嘱累"二字含殷勤付嘱之意，显示此经为佛法心要，当珍重视之、代代相传，为全经付嘱流通的重要环节。"
    },
    "chapter_25_yaowang_pin.txt": {
        "chapter_id": "chapter_25",
        "chapter_title": "妙法莲华经药王菩萨本事品第二十三",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《药王菩萨本事品》记述药王菩萨过去为一切众生喜见菩萨时，以苦行供养《法华经》的因缘。一切众生喜见菩萨为求正法，燃臂供养佛塔，又于日月净明德佛前燃身供养，历时千二百岁，以表对《法华经》的恭敬与誓愿。本品以燃身供佛的事例，彰显《法华经》的殊胜功德，以及菩萨为法忘躯的精进行持。药王菩萨为《法华经》流通的典范，本品劝勉众生以精进行持、身命供养来受持此经，体现了《法华经》难行能行、勇猛精进的菩萨精神。"
    },
    "chapter_26_miaoyin_pin.txt": {
        "chapter_id": "chapter_26",
        "chapter_title": "妙音菩萨品第二十四",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《妙音菩萨品》描述东方净光庄严世界妙音菩萨来娑婆世界礼拜供养释迦牟尼佛及多宝佛塔的因缘。妙音菩萨于过去久远劫中，已曾供养无量诸佛，深植德本，得三十二种变化身，能随类应身、普门示现。本品通过妙音菩萨的神通变化，展示《法华经》受持者所得的智慧与能力。又云妙音菩萨于过去九千亿佛所常受《法华经》，故能示现如此神通。本品体现了《法华经》的殊胜功德，以及菩萨受持此经后所得的种种利益与神通力。"
    },
    "chapter_27_guanshiyin_pin.txt": {
        "chapter_id": "chapter_27",
        "chapter_title": "妙法莲华经观世音菩萨普门品第二十五",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《观世音菩萨普门品》为《法华经》最为流传的独立篇章，记述观世音菩萨以大悲心普门示现、救度众生的功德。无尽意菩萨请问观世音菩萨得名的因缘，佛告之以大悲愿力，闻声救苦，令众生脱离水火、罗刹、刀杖、枷锁等七难，离贪、嗔、痴三毒，满求男、求女二求。本品详述观世音菩萨三十二应身，随众生应以何身得度者即现何身而为说法，体现"普门"之义——普遍、平等、无碍的救度法门。本品在中国佛教影响深远，成为观音信仰的核心经典，体现了大乘佛教慈悲济世的精神。"
    },
    "chapter_28_tuoluoni_pin.txt": {
        "chapter_id": "chapter_28",
        "chapter_title": "妙法莲华经陀罗尼品第二十六",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《陀罗尼品》为药王菩萨、勇施菩萨及四天王等宣说神咒，护持《法华经》。陀罗尼即总持，能持善法、遮恶法，为密咒之义。药王菩萨说咒护持读诵《法华经》者，令其安乐、离诸恶鬼侵害。勇施菩萨说咒护持法师，令离夜叉、罗刹等怖畏。毗沙门天王、持国天王等四天王亦各说咒，护持是经及受持者。本品体现了《法华经》与密宗陀罗尼的结合，显示此经为诸佛所护持、龙天所敬仰，受持者能得龙天护佑、远离怖畏。"
    },
    "chapter_29_miaozhuangyan_pin.txt": {
        "chapter_id": "chapter_29",
        "chapter_title": "妙法莲华经妙庄严王本事品第二十七",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《妙庄严王本事品》记述过去云雷音宿王华智佛时，净藏、净眼二王子与父妙庄严王共同修学《法华经》的因缘。妙庄严王本信外道婆罗门法，二王子示现神通力，令父王心生正信，入王园中说法，使王及夫人、后宫皆得法益。本品说明妙庄严王即今华德菩萨，二王子即药王、药上菩萨。本品通过一家父子共同修学的事例，说明《法华经》能转化邪见、令众生入佛道，体现了此经的广大摄受力，以及家庭共修、彼此度化的佛教家庭观。"
    },
    "chapter_30_puxian_pin.txt": {
        "chapter_id": "chapter_30",
        "chapter_title": "妙法莲华经普贤菩萨劝发品第二十八",
        "chapter_type": "经",
        "year": "后秦",
        "analysis": "《普贤菩萨劝发品》为《法华经》最后一品，普贤菩萨于佛前发愿护持《法华经》。本品中，普贤菩萨自东方宝威德上王佛国来至娑婆世界，劝发众生受持《法华经》，并宣说此经功德：若有人受持读诵，解其义趣，是人命终当生忉利天、兜率天，乃至最终成佛。普贤菩萨又发愿于恶世中护持是经，乘六牙白象王现其人前，供养守护。本品总结了《法华经》的全经功德，以普贤菩萨的弘愿为收束，体现了此经的究竟圆满，以及菩萨护法弘法的悲心。本品为全经圆满流通之终章。"
    },
    "chapter_31_hou_xu.txt": {
        "chapter_id": "chapter_31",
        "chapter_title": "妙法莲华经后序",
        "chapter_type": "序",
        "year": "后秦",
        "analysis": "此篇为《法华经》后序，僧睿所述。僧睿为鸠摩罗什四大弟子之一，参与《法华经》的译场工作。后序简要记述了翻译此经的因缘，以及对此经的赞叹。序文指出此经为"诸佛之秘藏，众经之实体"，阐明其在大乘佛教中的核心地位。后序还提及译经时的殊胜感应，以及大众闻法欢喜的情形。此序为《法华经》翻译史的珍贵资料，也是研究后秦佛教与鸠摩罗什译经事业的重要文献。"
    }
}


def parse_chapter_file(filepath):
    """解析篇章文件，提取段落"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 按 [数字] 分割段落
    pattern = r'\[(\d+)\]\n'
    parts = re.split(pattern, content)

    paragraphs = []
    # parts[0] 是开头空白或标题前内容，忽略
    # parts[1], parts[2] ... 是序号和内容交替
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            seq = int(parts[i])
            para_content = parts[i + 1].strip()
            if para_content:  # 忽略空段落
                paragraphs.append({
                    'seq': seq,
                    'content': para_content
                })

    return paragraphs


def generate_translation(content, chapter_type, is_verse=False):
    """生成译文 - 返回空字符串，实际翻译由人工或LLM生成"""
    # 这里返回标记，表示需要生成译文
    return ""


def generate_notes(content):
    """生成注释 - 返回空字符串"""
    return ""


def process_all_chapters():
    """处理所有篇章"""
    manifest = {
        "workflow_id": "classical-text-to-csv",
        "run_id": "run_20260322131217_b1c7f282",
        "node_id": "chapter_metadata_enrichment",
        "processed_at": "2026-03-26T10:00:00+00:00",
        "total_chapters": 31,
        "chapters": []
    }

    for filename in sorted(CHAPTER_INFO.keys()):
        info = CHAPTER_INFO[filename]
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename.replace('.txt', '.json'))

        print(f"Processing {filename}...")

        # 解析段落
        paragraphs = parse_chapter_file(input_path)

        # 生成丰富的段落数据
        enriched_paragraphs = []
        for para in paragraphs:
            enriched_paragraphs.append({
                "seq": para['seq'],
                "content": para['content'],
                "translation": "",  # 待填充
                "notes": ""
            })

        # 构建输出
        output = {
            "chapter_id": info['chapter_id'],
            "chapter_title": info['chapter_title'],
            "chapter_type": info['chapter_type'],
            "year": info['year'],
            "analysis": info['analysis'],
            "paragraphs": enriched_paragraphs
        }

        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        # 添加到manifest
        manifest['chapters'].append({
            "chapter_id": info['chapter_id'],
            "filename": filename.replace('.txt', '.json'),
            "title": info['chapter_title'],
            "type": info['chapter_type'],
            "paragraph_count": len(enriched_paragraphs)
        })

        print(f"  -> Saved {output_path} ({len(enriched_paragraphs)} paragraphs)")

    # 保存manifest
    manifest_path = "/Users/wuyuheng/Documents/Projects/Pipeliner/.pipeliner/runs/classical-text-to-csv/run_20260322131217_b1c7f282/artifacts/metadata_enrichment_manifest@v7/payload/metadata_enrichment_manifest.txt"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\nManifest saved to {manifest_path}")
    print(f"Total chapters processed: {len(manifest['chapters'])}")


if __name__ == "__main__":
    process_all_chapters()
