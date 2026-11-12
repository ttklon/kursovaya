# -*- coding: utf-8 -*-
"""Парсер текста курсовой по ст. 228: H1/H2/H3, L (пункт списка), пустая строка = новый абзац."""
def parse(path):
    blocks, buf = [], []
    for line in open(path, encoding='utf-8'):
        s = line.rstrip('\n')
        if s.startswith('L '):
            if buf:
                blocks.append(('p', ' '.join(buf).strip())); buf = []
            blocks.append(('item', s[2:].strip()))
        elif s.startswith(('H1 ', 'H2 ', 'H3 ')):
            if buf:
                blocks.append(('p', ' '.join(buf).strip())); buf = []
            blocks.append((s[:2].lower(), s[3:].strip()))
        elif not s.strip():
            if buf:
                blocks.append(('p', ' '.join(buf).strip())); buf = []
        else:
            buf.append(s.strip())
    if buf:
        blocks.append(('p', ' '.join(buf).strip()))
    return blocks
