# -*- coding: utf-8 -*-
"""Сборка docx и pdf из tz2/*.txt: docx — шаблон БЮИ, pdf — собственный рендер."""
import sys, os, shutil, json, re
sys.path.insert(0, '/home/user/work')
sys.path.insert(0, '/home/user/work/tz2')
import mk
import engine
import render_pdf as R
from build_obj import fix_fonts, align_list, set_props

TITLE = 'Уголовный закон: понятие, значение, задачи и принципы'
BLOCKS = []
for f in ('01.txt', '02.txt', '03.txt', '04.txt', '05.txt'):
    BLOCKS += mk.parse('/home/user/work/tz2/' + f)


def blocks_for_pdf():
    fn_text, items, toc = [], [], []
    in_src = False
    for kind, text in BLOCKS:
        def repl(m):
            fn_text.append(m.group(1).strip())
            return '[[fn:%d]]' % len(fn_text)
        t2 = re.sub(r'\[\[fn:(.+?)\]\]', repl, text)
        items.append((kind, t2))
        if kind == 'h1':
            in_src = text.strip().startswith('СПИСОК')
            toc.append((0, text.strip(), text.strip()))
        elif kind == 'h2' and not in_src:
            toc.append((1, text.strip(), text.strip()))
    return {'items': items, 'toc': toc, 'fn_text': fn_text, 'item_no': 1}


def build_docx(out, pages):
    class W:
        pass
    W.TITLE = TITLE
    W.BLOCKS = BLOCKS
    d = engine.Doc()
    d.topic = TITLE
    for b in BLOCKS:
        k = b[0]
        if k == 'h1':
            d.h1(b[1])
            if b[1].startswith('СПИСОК'):
                d._in_sources = True
        elif k == 'h2':
            d.h2(b[1])
        elif k == 'h3':
            d.h3(b[1])
        elif k == 'p':
            d.p(b[1])
        elif k == 'first':
            d.first(b[1])
        elif k == 'item':
            d.item(b[1])
        elif k == 'blank':
            d.blank()
        else:
            raise ValueError(k)
    d.save(out, pages)
    return len(d.fns)


def locate(pdf, anchors):
    import pymupdf
    doc = pymupdf.open(pdf)
    texts = [re.sub(r'\s+', ' ', doc[i].get_text()) for i in range(doc.page_count)]
    res = {}
    for a in anchors:
        key = re.sub(r'\s+', ' ', a).strip()
        for i, t in enumerate(texts):
            if i < 2:
                continue
            if key in t:
                res[a] = i + 1
                break
    return res, doc.page_count, texts


if __name__ == '__main__':
    out_docx = '/home/user/work/tmpbuild/Курсовая_уголовный_закон_БЮИ.docx'
    out_pdf = '/home/user/work/tmpbuild/Курсовая_уголовный_закон_БЮИ.pdf'

    bl = blocks_for_pdf()
    anchors = [a for _, _, a in bl['toc']]
    n1 = R.make(blocks_for_pdf(), TITLE, '/tmp/pass1.pdf', {})
    pages1, _, _ = locate('/tmp/pass1.pdf', anchors)
    bl2 = blocks_for_pdf()
    n2 = R.make(bl2, TITLE, out_pdf, pages1)
    pages2, n2p, texts = locate(out_pdf, anchors)
    missing = [a for a in anchors if a not in pages2]
    fn_pdf = len(bl2['fn_text'])

    nfn = build_docx(out_docx, pages2)
    fix_fonts(out_docx)
    align_list(out_docx)
    set_props(out_docx)

    rep = {'pages_pdf': n2p, 'pages_docx': nfn and None, 'toc': pages2,
           'missing': missing, 'footnotes_pdf': fn_pdf, 'footnotes_docx': nfn,
           'chars': len(''.join(texts).replace('\n', '').replace(' ', ''))}
    open('/home/user/work/tmpbuild/last_build.json', 'w').write(
        json.dumps(rep, ensure_ascii=False, indent=1))
    print(json.dumps(rep, ensure_ascii=False, indent=1))
