# -*- coding: utf-8 -*-
"""Универсальная двухпроходная сборка курсовой работы БЮИ (DOCX + PDF).

Ожидает каталог с файлами 01.txt..05.txt (разметка H1/H2/H3, L, пустая строка = новый абзац,
сноски внутри текста вида [[fn:полный текст сноски]]).

Пример:
  python3 pipeline/build_kursovaya.py \\
    --work-dir works/07_terroristicheskiy_akt_205 \\
    --title "Уголовно-правовая характеристика террористического акта|(статья 205 УК РФ)" \\
    --out-name "Курсовая_уголовно-правовая_характеристика_террористический_акт_205_БЮИ" \\
    --keywords "уголовное право; террористический акт; статья 205 УК РФ"
"""
import argparse
import glob
import json
import os
import re
import sys

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)


def load_source_files(src_dir):
    from mk_parser import parse

    txts = sorted(glob.glob(os.path.join(src_dir, '0*.txt')))
    if not txts:
        raise FileNotFoundError(f'В каталоге {src_dir} не найдены файлы 0*.txt')
    blocks = []
    for p in txts:
        blocks += parse(p)
    return blocks, txts


def to_render_blocks(raw_blocks):
    import engine

    d = engine.Doc()
    items = []
    in_src = False
    for k, txt in raw_blocks:
        if k == 'h1':
            if txt.startswith('СПИСОК'):
                in_src = True
            d.toc.append((0, txt, txt))
            items.append(('h1', txt))
            continue
        if k == 'h2':
            if not in_src:
                d.toc.append((1, txt, txt))
            items.append(('h2', txt))
            continue
        if k == 'h3':
            items.append(('h3', txt))
            continue
        txt_n = re.sub(
            r'(?<![.!?…])\[\[fn:(.+?)\]\]\s+(?=[А-ЯЁ])',
            lambda m: '[[fn:%s]]. ' % m.group(1),
            txt,
        )
        out = []
        for part in re.split(r'(\[\[fn:.*?\]\])', txt_n, flags=re.S):
            if not part:
                continue
            if part.startswith('[[fn:'):
                d.fns.append(part[5:-2].strip())
                out.append('[[fn:%d]]' % len(d.fns))
            else:
                out.append(part)
        items.append((k, ''.join(out)))
    return {'toc': d.toc, 'items': items, 'fn_text': [engine.clean_fn(t) for t in d.fns]}


def find_toc_pages(pdf_path, toc):
    import pymupdf

    d = pymupdf.open(pdf_path)
    pt = [
        re.sub(r'\s+', ' ', re.sub(r'-\s*\n\s*', '-', d[i].get_text())).strip()
        for i in range(d.page_count)
    ]
    d.close()
    res = {}
    for _, txt, key in toc:
        needle = re.sub(r'\s+', ' ', txt).strip()
        for i in range(2, len(pt)):
            if needle in pt[i]:
                res[key] = i + 1
                break
    return res


def build(work_dir, title, out_name, keywords='', src_subdir='src'):
    try:
        import pymupdf  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            'Для рендера PDF нужен пакет pymupdf. Установите: pip install -r pipeline/requirements.txt'
        ) from exc

    import doc_utils
    import engine
    import render_pdf

    work_dir = os.path.abspath(work_dir)
    src_dir = os.path.join(work_dir, src_subdir)
    out_docx = os.path.join(work_dir, f'{out_name}.docx')
    out_pdf = os.path.join(work_dir, f'{out_name}.pdf')

    raw_blocks, txts = load_source_files(src_dir)
    rb = to_render_blocks(raw_blocks)

    # Проход 1: предварительный PDF для точных номеров страниц в ОГЛАВЛЕНИИ
    render_pdf.make(rb, title, out_pdf, {})
    toc_pages = find_toc_pages(out_pdf, rb['toc'])

    # Проход 2: финальный PDF с заполненным ОГЛАВЛЕНИЕМ и проверка стабилизации номеров
    render_pdf.BIG.clear()
    n_pages = render_pdf.make(rb, title, out_pdf, toc_pages)
    toc_pages_2 = find_toc_pages(out_pdf, rb['toc'])
    if toc_pages_2 != toc_pages:
        toc_pages = toc_pages_2
        render_pdf.BIG.clear()
        n_pages = render_pdf.make(rb, title, out_pdf, toc_pages)

    # Сборка DOCX с теми же точными номерами страниц
    d = engine.Doc()
    d.topic = title
    for k, txt in raw_blocks:
        if k == 'h1':
            d.h1(txt)
            if txt.startswith('СПИСОК'):
                d._in_sources = True
        elif k == 'h2':
            d.h2(txt)
        elif k == 'h3':
            d.h3(txt)
        elif k == 'p':
            d.p(txt)
        elif k == 'item':
            d.item(txt)
        else:
            raise ValueError(f'Неизвестный тип блока: {k}')
    d.save(out_docx, toc_pages)

    doc_utils.fix_fonts(out_docx)
    list_left = doc_utils.align_list(out_docx)
    clean_title = title.replace('|', ' ')
    doc_utils.set_props(out_docx, title=clean_title, keywords=keywords)
    pages, words, chars = doc_utils.update_app_meta(out_docx, out_pdf)
    rep = doc_utils.scan(out_docx, out_pdf)
    rep.update({
        'src_files': [os.path.basename(x) for x in txts],
        'docx': out_docx,
        'pdf': out_pdf,
        'pages': n_pages,
        'words_pdf': words,
        'chars_pdf': chars,
        'footnotes': len(d.fns),
        'list_left': list_left,
        'big_justify_gaps': len(render_pdf.BIG),
        'toc_pages': toc_pages,
        'missing_toc': [k for _, _, k in rb['toc'] if k not in toc_pages],
    })
    return rep


def main():
    ap = argparse.ArgumentParser(description='Сборка курсовой работы БЮИ (DOCX + PDF)')
    ap.add_argument('--work-dir', required=True, help='Каталог курсовой (содержит src/0*.txt)')
    ap.add_argument('--title', required=True, help='Тема работы (перенос строки через "|")')
    ap.add_argument('--out-name', required=True, help='Базовое имя выходных файлов без расширения')
    ap.add_argument('--keywords', default='', help='Ключевые слова для свойств DOCX')
    ap.add_argument('--src-subdir', default='src', help='Подкаталог с 0*.txt (по умолчанию src)')
    args = ap.parse_args()

    rep = build(args.work_dir, args.title, args.out_name, args.keywords, args.src_subdir)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
