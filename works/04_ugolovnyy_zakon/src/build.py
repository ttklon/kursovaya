# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0,'/home/user/work'); sys.path.insert(0,'/home/user/work/tz2')
import mk, engine
from build_obj import fix_fonts, align_list, set_props, meta, scan, pdf_of

class W: pass
W.TITLE = "Уголовный закон: понятие, значение, задачи и принципы"
W.BLOCKS = []
for f in ('01.txt','02.txt','03.txt','04.txt','05.txt'):
    W.BLOCKS += mk.parse('/home/user/work/tz2/'+f)

OUT = '/home/user/work/tz2/Курсовая_уголовный_закон_БЮИ.docx'

if __name__ == '__main__':
    res = engine.build(W, OUT)
    fix_fonts(OUT); align_list(OUT); set_props(OUT)
    pdf = pdf_of(OUT)
    pages, words, chars = meta(OUT, pdf)
    rep = scan(OUT, pdf)
    rep.update({'words': words, 'chars': chars, 'toc': res['toc'], 'missing': res['missing'], 'footnotes': res['footnotes']})
    print(json.dumps(rep, ensure_ascii=False, indent=1))
