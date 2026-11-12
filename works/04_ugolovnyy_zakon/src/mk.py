# -*- coding: utf-8 -*-
"""Парсер текста: строки H1/H2/H3, пустая строка = новый абзац, [[fn:ключ]] = сноска."""
import re, sys
sys.path.insert(0, '/home/user/work/tz')
import cit as C

def fn(key):
    key = key.strip()
    m = re.fullmatch(r'PL58\((\d+)\)', key)
    if m: return '%s, пункт %s' % (C.PL58, m.group(1))
    m = re.fullmatch(r'PL1\((\d+)\)', key)
    if m: return '%s, пункт %s' % (C.PL1, m.group(1))
    m = re.fullmatch(r'KS3P|KS1344|KS23P|ST10|FZ300|UKCODE', key)
    if m:
        return {'KS3P': C.KS3P, 'KS1344': C.KS1344, 'KS23P': C.KS23P,
                'ST10': C.ST10, 'FZ300': C.FZ300, 'UKCODE': C.UK}[key]
    m = re.fullmatch(r'(\w+)\((.+)\)', key)
    if not m: raise KeyError(key)
    name, arg = m.group(1), m.group(2).strip().strip('"')
    f = {'uk': C.uk, 'krf': C.krf, 'fz64': C.fz64, 'obr': C.obr, 'garb': C.garb, 'mor24': C.mor24,
         'mor20': C.mor20, 'mor25': C.mor25, 'tar': C.tar, 'poe': C.poe, 'bar': C.bar, 'fed': C.fed,
         'ego': C.ego, 'nif': C.nif, 'mal': C.mal, 'yak': C.yak, 'tsai': C.tsai, 'bag': C.bag,
         'kov': C.kov, 'ala': C.ala, 'beg': C.beg}[name]
    return f(arg)

def parse(path):
    blocks = []
    buf = []
    for line in open(path, encoding='utf-8'):
        s = line.rstrip('\n')
        if s.startswith('L '):
            if buf: blocks.append(('p', ' '.join(buf).strip())); buf = []
            blocks.append(('item', s[2:].strip()))
        elif s.startswith(('H1 ', 'H2 ', 'H3 ')):
            if buf: blocks.append(('p', ' '.join(buf).strip())); buf = []
            blocks.append((s[:2].lower(), s[3:].strip()))
        elif not s.strip():
            if buf: blocks.append(('p', ' '.join(buf).strip())); buf = []
        else:
            buf.append(s.strip())
    if buf: blocks.append(('p', ' '.join(buf).strip()))
    out = []
    for kind, text in blocks:
        if kind == 'p':
            text = re.sub(r'\[\[fn:([^\]]+)\]\]', lambda m: '[[fn:%s]]' % fn(m.group(1)), text)
        out.append((kind, text))
    return out
