# -*- coding: utf-8 -*-
"""Постобработка DOCX/PDF курсовой работы: шрифты заголовков, список литературы, метаданные и проверка вёрстки."""
import datetime
import re
import shutil
import zipfile


def _esc_xml(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def fix_fonts(path):
    """Убирает тематические шрифты у заголовков, чтобы Word не рисовал Calibri."""
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'word/styles.xml':
                s = data.decode('utf-8')
                for sid in ('Heading1', 'Heading2', 'Heading3', 'Heading4'):
                    m = re.search(r'<w:style [^>]*w:styleId="%s".*?</w:style>' % sid, s, flags=re.S)
                    if not m:
                        continue
                    blk = m.group(0)
                    nb = re.sub(r'\s+w:(?:ascii|hAnsi|eastAsia|cs)Theme="[^"]*"', '', blk)
                    s = s.replace(blk, nb)
                data = s.encode('utf-8')
            elif it.filename == 'word/theme/theme1.xml':
                s = data.decode('utf-8')
                s = re.sub(
                    r'<a:majorFont>\s*<a:latin typeface="[^"]*"',
                    '<a:majorFont><a:latin typeface="Times New Roman"',
                    s,
                )
                s = re.sub(
                    r'<a:minorFont>\s*<a:latin typeface="[^"]*"',
                    '<a:minorFont><a:latin typeface="Times New Roman"',
                    s,
                )
                data = s.encode('utf-8')
            zout.writestr(it, data)
    shutil.move(tmp, path)


def align_list(path):
    """Список использованных источников — выравнивание по левому краю (длинные URL не растягивают пробелы)."""
    tmp = path + '.tmp'
    n = 0
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'word/document.xml':
                x = data.decode('utf-8')
                marker = 'СПИСОК ИСПОЛЬЗОВАННЫХ ИСТОЧНИКОВ'
                if marker in x:
                    cut = x.index(marker)
                    head, tail = x[:cut], x[cut:]
                    parts = re.split(r'(?=<w:p>)', tail)
                    for k, p in enumerate(parts):
                        if k == 0 or '<w:numPr>' not in p or '<w:pPr>' not in p:
                            continue
                        p = re.sub(r'<w:jc w:val="[^"]*"/>', '', p, count=1)
                        p = p.replace('</w:pPr>', '<w:jc w:val="left"/></w:pPr>', 1)
                        parts[k] = p
                        n += 1
                    data = (head + ''.join(parts)).encode('utf-8')
            zout.writestr(it, data)
    shutil.move(tmp, path)
    return n


def set_props(path, title, subject='Курсовая работа по дисциплине «Уголовное право»', keywords=''):
    """Обновляет dc:title, dc:subject и cp:keywords без остаточных значений из шаблона."""
    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'docProps/core.xml':
                s = data.decode('utf-8')
                s = re.sub(
                    r'<dc:title\s*/>|<dc:title[^>]*>.*?</dc:title>',
                    '<dc:title>%s</dc:title>' % _esc_xml(title),
                    s,
                    flags=re.S,
                )
                s = re.sub(
                    r'<dc:subject\s*/>|<dc:subject[^>]*>.*?</dc:subject>',
                    '<dc:subject>%s</dc:subject>' % _esc_xml(subject),
                    s,
                    flags=re.S,
                )
                s = re.sub(
                    r'<cp:keywords\s*/>|<cp:keywords[^>]*>.*?</cp:keywords>',
                    '<cp:keywords>%s</cp:keywords>' % _esc_xml(keywords),
                    s,
                    flags=re.S,
                )
                data = s.encode('utf-8')
            zout.writestr(it, data)
    shutil.move(tmp, path)


def update_app_meta(path, pdf_path, modified_iso=None):
    """Записывает число страниц/слов/символов из PDF в docProps/app.xml."""
    import pymupdf

    if modified_iso is None:
        modified_iso = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    d = pymupdf.open(pdf_path)
    pages = d.page_count
    text = ''.join(p.get_text() for p in d)
    words = len(re.findall(r'[А-Яа-яЁёA-Za-z0-9-]+', text))
    chars = len(re.sub(r'\s', '', text))
    d.close()

    tmp = path + '.tmp'
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        names = set(zin.namelist())
        for it in zin.infolist():
            data = zin.read(it.filename)
            if it.filename == 'docProps/app.xml':
                s = data.decode('utf-8')
                s = re.sub(r'<Pages>\d+</Pages>', '<Pages>%d</Pages>' % pages, s)
                s = re.sub(r'<Words>\d+</Words>', '<Words>%d</Words>' % words, s)
                s = re.sub(r'<Characters>\d+</Characters>', '<Characters>%d</Characters>' % chars, s)
                data = s.encode('utf-8')
            elif it.filename == 'docProps/core.xml':
                s = data.decode('utf-8')
                s = re.sub(
                    r'(<dcterms:modified[^>]*>)[^<]*(</dcterms:modified>)',
                    r'\g<1>%s\g<2>' % modified_iso,
                    s,
                )
                data = s.encode('utf-8')
            zout.writestr(it, data)
        if 'word/comments.xml' not in names:
            zout.writestr(
                'word/comments.xml',
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\r\n'
                '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
            )
    shutil.move(tmp, path)
    return pages, words, chars


def scan(docx_path, pdf_path):
    """Базовый технический скан готовых DOCX и PDF: шрифты, висячие заголовки, пустые страницы, сноски."""
    import pymupdf

    rep = {}
    d = pymupdf.open(pdf_path)
    rep['pages'] = d.page_count
    fonts = {}
    for i, p in enumerate(d):
        for b in p.get_text('dict')['blocks']:
            for ln in b.get('lines', []):
                for sp in ln['spans']:
                    fonts.setdefault(sp['font'], []).append(i + 1)
    rep['fonts'] = {k: (len(set(v)), min(v)) for k, v in fonts.items()}
    orphan = []
    for i, p in enumerate(d):
        lines = [x.strip() for x in p.get_text().strip().split('\n') if x.strip()]
        if not lines or i == 0:
            continue
        last = lines[-1]
        if last.isupper() and len(last) > 5:
            orphan.append((i + 1, last[:50]))
    rep['orphan_headings'] = orphan
    rep['empty_pages'] = [i + 1 for i, p in enumerate(d) if len(p.get_text().strip()) < 3]
    d.close()

    with zipfile.ZipFile(docx_path) as z:
        x = z.read('word/document.xml').decode('utf-8')
        rep['fn_refs'] = len(re.findall(r'<w:footnoteReference', x))
    return rep
