# -*- coding: utf-8 -*-
"""Сборка курсовой работы в формате сданной работы № 1 (шаблон work/tpl/ref.docx)."""
import os, re, shutil, subprocess, zipfile, tempfile, sys

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
TPL = os.path.join(PIPELINE_DIR, 'templates', 'ref.docx')
TMP = tempfile.gettempdir()
FN_ID0 = 20

def clean_fn(t):
    t = re.sub(r'\s*//[^/]*?URL:.*?\(\u0434\u0430\u0442\u0430 \u043e\u0431\u0440\u0430\u0449\u0435\u043d\u0438\u044f: [^)]*\)\.?', '', t).strip()
    if not t.endswith('.'):
        t += '.'
    return t

def esc(t):
    return (t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))

# ---------- документ ----------
class Doc:
    def __init__(self):
        self.paras = []      # (kind, xml)
        self.fns = []        # list of text
        self.toc = []        # (level, text, anchor)

    # --- служебное ---
    def _fn_run(self, i):
        return ('<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:sz w:val="20"/>'
                '<w:szCs w:val="20"/><w:vertAlign w:val="superscript"/></w:rPr>'
                '<w:footnoteReference w:id="%d"/></w:r>' % i)

    def _runs(self, text):
        """Текст со вставками [[fn: ... ]] -> прогоны."""
        import re as _re
        text = _re.sub(r'(?<![.!?\u2026])\[\[fn:(.+?)\]\]\s+(?=[\u0410-\u042f\u0401])', lambda m: '[[fn:%s]]. ' % m.group(1), text)
        out = []
        prev_fn = False
        for part in re.split(r'(\[\[fn:.*?\]\])', text, flags=re.S):
            if not part:
                continue
            if part.startswith('[[fn:'):
                body = part[5:-2].strip()
                self.fns.append(body)
                if prev_fn:
                    out.append('<w:r><w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/>'
                               '<w:vertAlign w:val="superscript"/></w:rPr><w:t>,</w:t></w:r>')
                out.append(self._fn_run(FN_ID0 + len(self.fns) - 1))
                prev_fn = True
            else:
                out.append('<w:r><w:t xml:space="preserve">%s</w:t></w:r>' % esc(part))
                if part.strip():
                    prev_fn = False
        return ''.join(out)

    # --- абзацы ---
    def p(self, text, style='BodyText'):
        self.paras.append('<w:p><w:pPr><w:pStyle w:val="%s"/></w:pPr>%s</w:p>'
                          % (style, self._runs(text)))

    def first(self, text):
        self.p(text, 'BodyText')

    def h1(self, text):
        self.paras.append(
            '<w:p><w:pPr><w:pStyle w:val="Heading1"/><w:pageBreakBefore/>'
            '<w:spacing w:after="120"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))
        self.toc.append((0, text, text))

    def h2(self, text, toc=True):
        self.paras.append(
            '<w:p><w:pPr><w:pStyle w:val="Heading2"/><w:keepNext/><w:pageBreakBefore w:val="0"/>'
            '<w:spacing w:before="120" w:after="120"/><w:ind w:firstLine="709"/><w:jc w:val="left"/></w:pPr>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))
        if toc and not getattr(self, '_in_sources', False):
            self.toc.append((1, text, text))

    def h3(self, text):
        self.paras.append(
            '<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:keepNext/>'
            '<w:spacing w:before="120" w:after="120"/><w:ind w:firstLine="0"/><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:rPr><w:b/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))

    def item(self, text):
        self.paras.append('<w:p><w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1001"/>'
                          '</w:numPr><w:ind w:left="720" w:hanging="480"/>'
                          '<w:jc w:val="both"/></w:pPr><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>' % esc(text))

    def blank(self):
        self.paras.append('<w:p><w:pPr><w:ind w:firstLine="0"/></w:pPr></w:p>')

    def pagebreak(self):
        self.paras.append('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    # --- титул ---
    def title_page(self, topic):
        def c(text, bold=False, jc='center'):
            b = '<w:b/>' if bold else '<w:b w:val="0"/>'
            return ('<w:p><w:pPr><w:spacing w:line="240" w:lineRule="auto" w:before="0" w:after="0"/>'
                    '<w:ind w:firstLine="0"/><w:jc w:val="%s"/></w:pPr><w:r><w:rPr><w:rFonts '
                    'w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>%s<w:sz w:val="28"/></w:rPr>'
                    '<w:t xml:space="preserve">%s</w:t></w:r></w:p>' % (jc, b, esc(text)))
        self.paras.append(c('Министерство внутренних дел Российской Федерации', True))
        self.paras.append(c('Федеральное государственное казенное образовательное учреждение высшего образования', False))
        self.paras.append(c('«Барнаульский юридический институт Министерства внутренних дел Российской Федерации»', True))
        self.paras.append(c('', False))
        self.paras.append(c('Кафедра уголовного права и криминологии', False))
        for _ in range(4):
            self.paras.append(c('', False))
        self.paras.append(c('КУРСОВАЯ РАБОТА', True))
        self.paras.append(c('по дисциплине «Уголовное право»', False))
        parts = topic.split('|')
        if len(parts) == 1:
            self.paras.append(c('на тему: «%s»' % parts[0], False))
        else:
            self.paras.append(c('на тему: «%s' % parts[0], False))
            for mid in parts[1:-1]:
                self.paras.append(c(mid, False))
            self.paras.append(c(parts[-1] + '»', False))
        for _ in range(4):
            self.paras.append(c('', False))
        self.paras.append(c('Выполнил(а): ______________________________', False, 'right'))
        self.paras.append(c('Научный руководитель: _____________________', False, 'right'))
        for _ in range(5):
            self.paras.append(c('', False))
        self.paras.append(c('Барнаул', False))
        self.paras.append(c('2026', False))
        self.pagebreak()

    # --- оглавление ---
    def toc_page(self, pages):
        self.paras.append('<w:p><w:pPr><w:spacing w:line="360" w:lineRule="auto"/><w:ind w:firstLine="0"/>'
                          '<w:jc w:val="center"/></w:pPr><w:r><w:rPr><w:rFonts w:ascii="Times New Roman" '
                          'w:hAnsi="Times New Roman"/><w:b/><w:sz w:val="28"/></w:rPr>'
                          '<w:t>ОГЛАВЛЕНИЕ</w:t></w:r></w:p>')
        for lvl, text, anchor in self.toc:
            num = pages.get(anchor, '')
            left = '0' if lvl == 0 else '425'
            self.paras.append(
                '<w:p><w:pPr><w:tabs><w:tab w:pos="9354" w:val="right" w:leader="dot"/></w:tabs>'
                '<w:spacing w:line="360" w:lineRule="auto" w:before="0" w:after="0"/>'
                '<w:ind w:firstLine="0" w:left="%s" w:right="0"/><w:jc w:val="left"/></w:pPr>'
                '<w:r><w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
                '<w:sz w:val="28"/></w:rPr><w:t>%s</w:t><w:tab/><w:t>%s</w:t></w:r></w:p>'
                % (left, esc(text), esc(str(num))))

    # --- запись ---
    def save(self, out, pages=None):
        if pages is None:
            pages = {}
        content = list(self.paras)
        self.paras = []
        self.title_page(self.topic)
        self.toc_page(pages)
        body = self.paras + content
        self.paras = content

        doc_xml = HEAD + ''.join(body) + SECTPR + FOOT
        fns = FNHEAD + ''.join(
            '<w:footnote w:id="%d"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/></w:pPr>'
            '<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/><w:sz w:val="20"/><w:szCs w:val="20"/>'
            '<w:vertAlign w:val="superscript"/></w:rPr><w:footnoteRef/></w:r>'
            '<w:r><w:t xml:space="preserve"> </w:t></w:r>'
            '<w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p></w:footnote>'
            % (FN_ID0 + i, esc(clean_fn(t))) for i, t in enumerate(self.fns)) + '</w:footnotes>'

        zin = zipfile.ZipFile(TPL)
        zout = zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED)
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                data = doc_xml.encode('utf-8')
            elif item.filename == 'word/footnotes.xml':
                data = fns.encode('utf-8')
            elif item.filename == 'word/comments.xml':
                # пустой, но обязательный раздел: на него есть ссылка в document.xml.rels
                data = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                        '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'
                        ).encode('utf-8')
            zout.writestr(item, data)
        zout.close(); zin.close()
        return out


HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<w:body>')
SECTPR = ('<w:sectPr><w:headerReference w:type="first" r:id="rId9"/><w:headerReference w:type="default" '
          'r:id="rId10"/><w:footnotePr><w:numRestart w:val="eachPage"/></w:footnotePr>'
          '<w:pgSz w:h="16837" w:w="11905"/><w:pgMar w:bottom="1133" w:footer="720" w:gutter="0" '
          'w:left="1700" w:right="566" w:top="1133"/><w:cols w:space="720"/><w:docGrid w:linePitch="360"/>'
          '<w:titlePg/></w:sectPr>')
FOOT = '</w:body></w:document>'
FNHEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
          '<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
          '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>'
          '<w:footnote w:type="separator" w:id="-1"><w:p><w:r><w:separator/></w:r></w:p></w:footnote>')


def to_pdf(docx):
    os.makedirs(TMP, exist_ok=True)
    subprocess.run(['soffice', '--headless', '--convert-to', 'pdf', '--outdir', TMP, docx],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
    return os.path.join(TMP, os.path.splitext(os.path.basename(docx))[0] + '.pdf')


def page_texts(pdf):
    out = subprocess.run(['pdftotext', '-layout', pdf, '-'], capture_output=True, check=True).stdout.decode('utf-8')
    return out.split('\f')


def locate(pdf, anchors):
    pages = page_texts(pdf)
    res = {}
    for a in anchors:
        key = re.sub(r'\s+', ' ', a).strip()
        for i, t in enumerate(pages):
            if i < 2:            # титул и оглавление не считаем
                continue
            if key in re.sub(r'-\s+', '-', re.sub(r'\s+', ' ', t)):
                res[a] = i + 1
                break
    return res, len(pages) - 1 if pages and not pages[-1].strip() else len(pages)


def build(work, out):
    d = Doc(); d.topic = work.TITLE
    for b in work.BLOCKS:
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
    anchors = [a for _, _, a in d.toc]
    d.save(out)
    pdf = to_pdf(out)
    pages, n = locate(pdf, anchors)
    missing = [a for a in anchors if a not in pages]
    d.save(out, pages)
    pdf = to_pdf(out)
    pages2, n2 = locate(pdf, anchors)
    return {'pages': n2, 'toc': pages2, 'missing': missing, 'footnotes': len(d.fns), 'pdf': pdf}
