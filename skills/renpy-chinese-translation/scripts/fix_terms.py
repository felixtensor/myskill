#!/usr/bin/env python3
"""
Post-translation terminology fixer.
Ensures key terms match the established Chinese translations from 0characters.rpy and 0constants.rpy.
"""

import re
import sys

TERM_FIXES = [
    # Safe Chinese mistranslations produced by machine translation.
    # Ambiguous cases such as "灰色" (Grey vs. color), "本质" (Essence vs.
    # ordinary meaning), and broad "审判" (Trial vs. judgment) are reported by
    # translation_guard.py and left for review.
    (r'哈罗|哈喽', '海洛'),
    (r'格瑞', '格雷'),
    (r'埃利', '艾利'),
    (r'“灰色的”', '“格雷”'),
    (r'灰色的([？！…])', r'格雷\1'),
    (r'(海洛|霍恩|艾利|格雷|洛克|杰拉德|瑞尚|凯登|格洛丽亚)[ \t]+([\u3400-\u9fff])', r'\1\2'),
    (r'([\u3400-\u9fff，。！？、；：（“])[ \t]+(海洛|霍恩|艾利|格雷|洛克|杰拉德|瑞尚|凯登|格洛丽亚)', r'\1\2'),
    (r'\u200b', ''),
    (r'……。', '……'),
    (r'\.{2,}。', '……'),
    (r'\.{2,}', '……'),
    (r'(?<=[\u3400-\u9fff])\.(?!\.)', '。'),
    (r'枢纽生物|枢纽存在|枢纽生命', '羁绊之魂'),
    (r'联系状态|枢纽状态', '羁绊状态'),
    (r'灵枢仪式|枢纽仪式|Nexus仪式', '羁绊仪式'),
    (r'枢纽石|Nexus石', '羁绊之石'),
    (r'监护人', '守护者'),
    (r'伴游|陪护', '陪侍'),
    (r'至尊主', '至高存在'),
    (r'至高无上的存在', '至高存在'),
    (r'至高无上(?!的)', '至高存在'),
    (r'精华液', '精华'),
    (r'我的本质', '我的精华'),
    (r'我们的本质', '我们的精华'),
    (r'本质能够', '精华能够'),
    (r'什么？本质？', '什么？精华？'),
    (r'通过本质', '通过精华'),
    (r'七大考验|七个试炼', '七项试炼'),

    # Terms from 0constants.rpy
    (r'(?<![A-Za-z0-9_])Purgatory(?![A-Za-z0-9_])', '炼狱'),
    (r'(?<![A-Za-z0-9_])Nexus Being(?![A-Za-z0-9_])', '羁绊之魂'),
    (r'(?<![A-Za-z0-9_])Nexus State(?![A-Za-z0-9_])', '羁绊状态'),
    (r'(?<![A-Za-z0-9_])Seven Trials(?![A-Za-z0-9_])', '七项试炼'),
    (r'(?<![A-Za-z0-9_])the Trials(?![A-Za-z0-9_])', '试炼'),
    (r'(?<![A-Za-z0-9_])Trials(?![A-Za-z0-9_])', '试炼'),
    (r'(?<![A-Za-z0-9_])Guardians(?![A-Za-z0-9_])', '守护者'),
    (r'(?<![A-Za-z0-9_])Guardian(?![A-Za-z0-9_])', '守护者'),
    (r'(?<![A-Za-z0-9_])Essence(?![A-Za-z0-9_])', '精华'),
    (r'(?<![A-Za-z0-9_])the Gate(?![A-Za-z0-9_])', '那扇门'),
    (r'(?<![A-Za-z0-9_])Gate(?![A-Za-z0-9_])', '门'),

    # Character names
    (r'(?<![A-Za-z0-9_])Haelo(?![A-Za-z0-9_])', '海洛'),
    (r'(?<![A-Za-z0-9_])Horne(?![A-Za-z0-9_])', '霍恩'),
    (r'(?<![A-Za-z0-9_])Grey(?![A-Za-z0-9_])', '格雷'),
    (r'(?<![A-Za-z0-9_])Elie(?![A-Za-z0-9_])', '艾利'),
    (r'(?<![A-Za-z0-9_])Locke(?![A-Za-z0-9_])', '洛克'),
    (r'(?<![A-Za-z0-9_])Gerrard(?![A-Za-z0-9_])', '杰拉德'),
    (r'(?<![A-Za-z0-9_])Gerrand(?![A-Za-z0-9_])', '杰兰德'),
    (r'(?<![A-Za-z0-9_])Rishaan(?![A-Za-z0-9_])', '瑞尚'),
    (r'(?<![A-Za-z0-9_])Kayden(?![A-Za-z0-9_])', '凯登'),
    (r'(?<![A-Za-z0-9_])Gloria(?![A-Za-z0-9_])', '格洛丽亚'),
    (r'(?<![A-Za-z0-9_])Justin(?![A-Za-z0-9_])', '贾斯汀'),
    (r'(?<![A-Za-z0-9_])Paulo(?![A-Za-z0-9_])', '保罗'),
    (r'(?<![A-Za-z0-9_])Karen(?![A-Za-z0-9_])', '凯伦'),

    # Titles
    (r'(?<![A-Za-z0-9_])Supreme Being(?![A-Za-z0-9_])', '至高存在'),
    (r'(?<![A-Za-z0-9_])Supreme One(?![A-Za-z0-9_])', '至高者'),
    (r'(?<![A-Za-z0-9_])Archangel(?![A-Za-z0-9_])', '大天使'),
    (r'(?<![A-Za-z0-9_])Overlord(?![A-Za-z0-9_])', '大领主'),

    # Location/Concept
    (r'(?<![A-Za-z0-9_])Seven Nexus(?![A-Za-z0-9_])', '七重羁绊'),
    (r'(?<![A-Za-z0-9_])Nexus Ritual(?![A-Za-z0-9_])', '羁绊仪式'),
    (r'(?<![A-Za-z0-9_])Nexus Stone(?![A-Za-z0-9_])', '羁绊之石'),
    (r'(?<![A-Za-z0-9_])Nexus(?![A-Za-z0-9_])', '羁绊'),
]


def is_reference_or_control_line(line):
    """Return True for lines that must not be edited by terminology fixes."""
    stripped = line.lstrip()
    return (
        stripped.startswith('#')
        or stripped.startswith('old ')
        or stripped.startswith('voice ')
        or stripped.startswith('translate ')
        or not stripped
    )


def fix_file(filepath):
    """Apply terminology fixes only to translated dialogue/new lines."""
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    changes = 0
    for i, line in enumerate(lines):
        # NEVER modify reference/control lines. In Ren'Py tl files, both
        # comments and old "..." strings are lookup keys, not translations.
        if is_reference_or_control_line(line):
            continue
        for pattern, replacement in TERM_FIXES:
            new_line, count = re.subn(pattern, replacement, line)
            if count > 0:
                lines[i] = new_line
                changes += count

    if changes > 0:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        print(f"  {filepath}: {changes} terminology fixes applied")
    else:
        print(f"  {filepath}: no fixes needed")

    return changes


if __name__ == '__main__':
    total = 0
    for fp in sys.argv[1:]:
        total += fix_file(fp)
    print(f"\nTotal terminology fixes: {total}")
