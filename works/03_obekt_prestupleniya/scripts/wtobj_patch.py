# -*- coding: utf-8 -*-
"""Патч депаттернизации: подменяет прозу блоков, сохраняя сноски в прежнем порядке."""
import re
import wtobj
import new_a, new_b

NEW = {}
NEW.update(new_a.NEW)
NEW.update(new_b.NEW)

TITLE = wtobj.TITLE
BLOCKS = []
for i, b in enumerate(wtobj.BLOCKS):
    if i in NEW and NEW[i] == '':
        continue
    if i not in NEW or b[0] != 'p':
        BLOCKS.append(b)
        continue
    old = b[1]
    fns = re.findall(r'\[\[fn:(.*?)\]\]', old, flags=re.S)
    text = NEW[i]
    need = text.count('{F}')
    assert need == len(fns), (i, need, len(fns))
    it = iter(fns)
    text = re.sub(r'\{F\}', lambda m: '[[fn:%s]]' % next(it), text)
    BLOCKS.append(('p', text))
assert len(BLOCKS) == len(wtobj.BLOCKS) - sum(1 for i in NEW if NEW[i] == '')
H2 = {'2.1. Классификация объектов преступления по вертикали': '2.1. Классификация объектов по вертикали'}
BLOCKS = [(b[0], H2.get(b[1], b[1])) if b[0] == 'h2' else b for b in BLOCKS]
