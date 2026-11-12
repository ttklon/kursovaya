# -*- coding: utf-8 -*-
"""Вёрстка PDF курсовой работы по метрикам эталонного файла:
A4; поля 30/10/20/20 мм; кегль 14, интервал 1,5 (24,15); отступ 35,45;
сноски 12 постранично с нумерацией с 1 на каждой странице."""
import os
import re
import pymupdf
from pymupdf import Font

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(PIPELINE_DIR, 'fonts') + os.sep
FP = {'r': F + 'LiberationSerif-Regular.ttf', 'b': F + 'LiberationSerif-Bold.ttf'}
REG, BOLD = Font(fontfile=FP['r']), Font(fontfile=FP['b'])
ASC = REG.ascender           # доля кегля

PW, PH = 595.28, 841.89
LEFT, TEXT_W = 85.10, 481.83
RIGHT = LEFT + TEXT_W
TOC_RIGHT = 552.80
BODY, LH, IND = 14.0, 24.15, 35.45
H1TOP, AFTER = 57.28, 30.15
FOOT, FLH = 12.0, 13.60
FN_NUM_W = 17.79
BODY_BOT = 782.30            # базовая линия последней строки основного текста
FN_BOT = 782.65              # базовая линия последней строки сносок
GAP_FN = 37.0               # от базовой строки тела до верха блока сносок
SEP_DY = 7.50                # линия-разделитель выше первой сноски


def asc(size):
    return ASC * size


SEP = []
BIG = []
FNMAP = {}          # сквозной номер сноски -> номер на текущей странице


def page_line(tw, y):
    SEP.append(y)


class Mark:
    __slots__ = ('num',)
    def __init__(self, n):
        self.num = n


def w(t, size=BODY, bold=False):
    return (BOLD if bold else REG).text_length(t, size)


def toks(text):
    # неразрывный пробел не должен попадать в разбиение по \s+:
    # иначе «39 134» рвётся по границе разрядов
    text = text.replace('\u00a0', '\x01')
    out, pos = [], 0
    for m in re.finditer(r'\[\[fn:(\d+)\]\]', text):
        out += [x for x in re.split(r'(\s+)', text[pos:m.start()]) if x]
        out.append(Mark(int(m.group(1))))
        pos = m.end()
    out += [x for x in re.split(r'(\s+)', text[pos:]) if x]
    out = [' ' if (isinstance(x, str) and x.strip() == '') else x for x in out]
    res = []
    for t in out:
        if isinstance(t, str) and t != ' ' and '://' in t:
            # адрес режется по «/» на любые части: Word переносит так же,
            # иначе строка с «URL:» обрывается задолго до поля
            for a in re.split(r'(?<=/)', t):
                if not a:
                    continue
                if w(a) > TEXT_W * 0.8:
                    res += split_long(a, TEXT_W * 0.8)
                else:
                    res.append(a)
        elif isinstance(t, str) and t != ' ' and w(t) > TEXT_W * 0.8:
            res += split_long(t, TEXT_W * 0.8)
        else:
            res.append(t)
    return [x.replace('\x01', '\u00a0') if isinstance(x, str) else x for x in res]


def split_long(t, limit):
    """Длинный токен (URL) режется по «/», «-», «.» и лишь затем посимвольно."""
    import re as _re
    atoms = [a for a in _re.split(r'(?<=[/\-.?&=])', t) if a]
    parts, cur = [], ''
    for a in atoms:
        if w(cur + a) <= limit or not cur:
            if w(cur + a) <= limit:
                cur += a
                continue
            parts.append(cur)
            cur = a
        else:
            parts.append(cur)
            cur = a
    if cur:
        parts.append(cur)
    res = []
    for p in parts:
        if w(p) <= limit:
            res.append(p)
            continue
        cur, cw = '', 0.0
        for ch in p:
            cwid = w(ch)
            if cw + cwid > limit and cur:
                res.append(cur); cur, cw = ch, cwid
            else:
                cur += ch; cw += cwid
        if cur:
            res.append(cur)
    return res


def twidth(t, size=BODY, bold=False):
    if isinstance(t, Mark):
        return w(str(FNMAP.get(t.num, t.num)), 7.0)
    return w(t, size, bold)


def measure(ts, size=BODY, bold=False):
    s = 0.0
    for i, t in enumerate(ts):
        s += twidth(t, size, bold)
        if isinstance(t, Mark) and i + 1 < len(ts) and isinstance(ts[i + 1], Mark):
            s += w(',', 7.0)
    return s


def clusters(ts):
    """Склеивает слово и идущие за ним знаки сносок в один кластер."""
    out, i = [], 0
    while i < len(ts):
        if ts[i] == ' ':
            out.append([i]); i += 1
            continue
        c = [i]; i += 1
        while i < len(ts) and isinstance(ts[i], Mark):
            c.append(i); i += 1
        out.append(c)
    return out


def wrap1(ts, indent, limit, size=BODY, bold=False):
    """Первая строка набора: (строка, число израсходованных токенов)."""
    cl = clusters(ts)
    avail = limit - indent
    taken, cw = 0, 0.0
    for grp in cl:
        wid = sum(twidth(ts[i], size, bold) for i in grp)
        nm = sum(1 for i in grp if isinstance(ts[i], Mark))
        if nm > 1:
            wid += (nm - 1) * w(',', 7.0)
        first_ch = ts[grp[0]]
        hang = (isinstance(first_ch, str) and first_ch.strip()
                and first_ch.strip()[0] in ',.;:!?%)»' and taken)
        if cw + wid <= avail + 0.01 or hang:
            taken = grp[-1] + 1
            cw += wid
            continue
        break
    line = ts[:taken]
    while line and line[-1] == ' ':
        line.pop()
    if not line and ts:
        line = [ts[0]]
        taken = 1
    return line, len(line)


def put(tw, text, x, y, size=BODY, bold=False):
    tw.append((x, y), text, font=BOLD if bold else REG, fontsize=size)


def line_out(tw, ts, x, y, limit, justify=False, size=BODY, bold=False):
    nat = measure(ts, size, bold)
    sp = sum(1 for t in ts if t == ' ')
    extra = 0.0
    if justify and sp and nat < limit:
        extra = (limit - nat) / sp
        if extra <= 0:
            extra = 0.0
        if extra > 16.0:          # предел растяжки межсловных пробелов
            BIG.append(round(extra, 1))
            extra = 16.0          # остаток уходит в концевой пробел строки
    cx, buf = x, ''
    for pos, t in enumerate(ts):
        prev_mark = pos > 0 and isinstance(ts[pos - 1], Mark)
        if isinstance(t, Mark):
            if buf:
                put(tw, buf, cx, y, size, bold); cx += w(buf, size, bold); buf = ''
            s = str(FNMAP.get(t.num, t.num))
            if prev_mark:
                put(tw, ',', cx, y - (asc(size) - asc(7.0)), 7.0)
                cx += w(',', 7.0)
            put(tw, s, cx, y - (asc(size) - asc(7.0)), 7.0)
            cx += w(s, 7.0)
        elif t == ' ':
            if buf:
                put(tw, buf, cx, y, size, bold); cx += w(buf, size, bold); buf = ''
            nxt = ts[pos + 1] if pos + 1 < len(ts) else None
            e = 0.0 if isinstance(nxt, Mark) else extra
            cx += e / 2.0
            put(tw, ' ', cx, y, size, bold)
            cx += w(' ', size, bold) + e / 2.0
        else:
            buf += t
    if buf:
        put(tw, buf, cx, y, size, bold)


def center(tw, text, y, size=BODY, bold=False):
    put(tw, text, LEFT + (TEXT_W - w(text, size, bold)) / 2, y, size, bold)


def foot_lines(text, width=TEXT_W - FN_NUM_W):
    out, cur, cw = [], [], 0.0
    lim = width
    for t in re.split(r'(\s+)', text):
        if not t:
            continue
        if t.strip() == '':
            t = ' '
        if not cur and t == ' ':
            continue
        tw = w(t, FOOT)
        if cw + tw <= lim + 0.01:
            cur.append(t); cw += tw
        else:
            while cur and cur[-1] == ' ':
                cur.pop()
            out.append(cur)
            cur, cw, lim = [t], tw, TEXT_W
    if cur:
        while cur and cur[-1] == ' ':
            cur.pop()
        out.append(cur)
    return out


def draw_foot(tw, fns, first_top):
    if not fns:
        return
    seq = []
    for num, text, _g in fns:
        off = w(str(num), 7.0) + w(' ', FOOT)
        lns = foot_lines(text, TEXT_W - off)
        for k, ln in enumerate(lns):
            seq.append((num if k == 0 else None, ln, off, k < len(lns) - 1))
    page_line(tw, first_top - SEP_DY)
    y = first_top + asc(FOOT)
    for num, ln, off, just in seq:
        if num is not None:
            put(tw, str(num), LEFT, y - (asc(FOOT) - asc(7.0)), 7.0)
            line_out(tw, ln, LEFT + off, y, TEXT_W - off, just, FOOT)
        else:
            line_out(tw, ln, LEFT, y, TEXT_W, just, FOOT)
        y += FLH


class Builder:
    def __init__(self, blocks, title):
        self.blocks, self.title = blocks, title
        self._cont_first = False
        self.doc = pymupdf.open()

    def title_page(self):
        page = self.doc.new_page(width=PW, height=PH)
        _parts = self.title.split('|')
        _theme = 'на тему: «%s' % _parts[0] + ('»' if len(_parts) == 1 else '')
        rows = [
            (57.28, 'Министерство внутренних дел Российской Федерации', True),
            (73.38, 'Федеральное государственное казенное образовательное учреждение', False),
            (89.48, 'высшего образования', False),
            (105.58, '«Барнаульский юридический институт Министерства внутренних дел', True),
            (121.68, 'Российской Федерации»', True),
            (153.88, 'Кафедра уголовного права и криминологии', False),
            (234.38, 'КУРСОВАЯ РАБОТА', True),
            (250.48, 'по дисциплине «Уголовное право»', False),
            (266.58, _theme, False),
            (347.08, 'Выполнил(а): ______________________________', False),
            (363.18, 'Научный руководитель: _____________________', False),
            (459.78, 'Барнаул', False),
            (475.88, '2026', False),
        ]
        parts = self.title.split('|')
        if len(parts) > 1:
            extra = [(282.68 + 16.10 * idx, p + ('»' if idx == len(parts) - 2 else ''), False)
                     for idx, p in enumerate(parts[1:])]
            rows = rows[:9] + extra + rows[9:]
        tw = pymupdf.TextWriter(page.rect)
        for y, text, bold in rows:
            yb = y + asc(BODY)
            if text.startswith(('Выполнил', 'Научный')):
                put(tw, text, RIGHT - w(text), yb)
            else:
                center(tw, text, yb, BODY, bold)
        tw.write_text(page)
        return page

    def toc_page(self, toc_pages, number):
        page = self.doc.new_page(width=PW, height=PH)
        tw = pymupdf.TextWriter(page.rect)
        center(tw, str(number), 36.51 + asc(12), 12)
        center(tw, 'ОГЛАВЛЕНИЕ', H1TOP + asc(BODY), BODY, True)
        y = H1TOP + asc(BODY) + LH + 0.0
        for lvl, text, key in self.blocks['toc']:
            text = text.strip()
            num = str(toc_pages.get(key, ''))
            x = LEFT if lvl == 0 else LEFT + 21.25
            lines = self._lines_of(toks(text), 'item')
            nw = w(num) if num else 0.0
            for li, ln in enumerate(lines):
                last = (li == len(lines) - 1)
                line_out(tw, ln, x, y, TEXT_W - (x - LEFT), False)
                if last:
                    wt = measure(ln)
                    d = w('.')
                    k = int((TOC_RIGHT - nw - 3 - (x + wt + 2)) / d)
                    if k > 0:
                        put(tw, '.' * k, x + wt + 2, y)
                    if num:
                        put(tw, num, TOC_RIGHT - nw, y)
                y += LH
        tw.write_text(page)
        return page

    # --- раскладка страницы: построчно, с учётом места под сноски ---
    def _lines_of(self, ts, kind):
        out, first = [], True
        while ts:
            if kind == 'item':
                ln, used = wrap1(ts, 0, TEXT_W - 36.0)
            else:
                ln, used = wrap1(ts, IND if first else 0, TEXT_W)
            rest = ts[used:]
            while rest and rest[0] == ' ':
                rest = rest[1:]
            out.append(ln)
            ts = rest
            first = False
        return out

    def _fnlen(self, num):
        t = self.blocks['fn_text'][num - 1]
        off = w(str(1), 7.0) + w(' ', FOOT)
        return len(foot_lines(t, TEXT_W - off))

    def layout(self, pi, cont, start_y, with_foot=True):
        items = self.blocks['items']
        F = self.blocks['fn_text']
        placed = []
        fns = []
        fnl = 0
        no = self.blocks['item_no']
        y = start_y
        while pi < len(items):
            kind, text = items[pi]
            if kind == 'h1':
                if placed:
                    break
                for ln in self._lines_of(toks(text), 'item'):
                    placed.append(('h1', ln, y, None))
                    y += LH
                y += AFTER - LH
                pi += 1; cont = None
                continue
            if kind in ('h2', 'h3'):
                reserve = 3 * LH
                lim_h = BODY_BOT if fnl == 0 else \
                    FN_BOT - (fnl - 1) * FLH - asc(FOOT) - GAP_FN
                if placed and y + reserve > lim_h - 0.01:
                    break
                for ln in self._lines_of(toks(text), 'item'):
                    placed.append((kind, ln, y, None))
                    y += LH
                y += (AFTER if kind == 'h2' else AFTER + 2.0) - LH
                pi += 1; cont = None
                continue
            ts = cont if cont is not None else toks(text)
            first = (cont is None) or getattr(self, '_cont_first', False)
            first0 = first
            para_start = len(placed)
            if first and placed and kind in ('p', 'item'):
                ls = self._lines_of(ts, kind)
                if len(ls) <= 4:
                    fn_add = 0
                    if with_foot:
                        for ln0 in ls:
                            for t0 in ln0:
                                if isinstance(t0, Mark):
                                    fn_add += self._fnlen(t0.num)
                    ntot = fnl + fn_add
                    lim = BODY_BOT if ntot == 0 else \
                        FN_BOT - (ntot - 1) * FLH - asc(FOOT) - GAP_FN
                    if y + (len(ls) - 1) * LH > lim + 0.01:
                        break
            while ts:
                if kind == 'item':
                    ln, used = wrap1(ts, 0, TEXT_W - 36.0)
                else:
                    ln, used = wrap1(ts, IND if first else 0, TEXT_W)
                rest = ts[used:]
                while rest and rest[0] == ' ':
                    rest = rest[1:]
                newfns = [t.num for t in ln if isinstance(t, Mark)]
                add = 0
                if with_foot:
                    for nf in newfns:
                        add += self._fnlen(nf)
                n_total = fnl + add
                allowed = BODY_BOT if n_total == 0 else \
                    FN_BOT - (n_total - 1) * FLH - asc(FOOT) - GAP_FN
                if y > allowed + 0.01:
                    break
                lastline = not rest
                if kind == 'item':
                    placed.append(('item', ln, y, (no if first else None, lastline)))
                    if first:
                        no += 1
                else:
                    placed.append(('p', ln, y, (IND if first else 0, lastline)))
                if with_foot:
                    for nf in newfns:
                        fnl += self._fnlen(nf)
                        fns.append((len(fns) + 1, F[nf - 1], nf))
                y += LH
                ts = rest
                first = False
            if ts:
                if kind in ('p', 'item'):
                    probe, used = wrap1(ts, 0, TEXT_W)
                    tail = self._lines_of(ts, kind)
                    single = len(tail) <= (2 if kind == 'item' else 1)
                    nl = len(placed) - para_start
                    if (single and nl >= 2) or nl == 1:
                        # если элемент списка целиком уехал на следующую страницу,
                        # уже израсходованный номер возвращается счётчику
                        if kind == 'item' and first0 and nl == 1:
                            no -= 1
                        tail = placed.pop()[1]
                        if tail and ts and not isinstance(ts[0], Mark) and tail[-1] != ' ':
                            ts = [' '] + ts
                        ts = tail + ts
                        if with_foot:
                            for t in tail:
                                if isinstance(t, Mark):
                                    fnl -= self._fnlen(t.num)
                                    fns.pop()
                self._cont_first = first0 if len(placed) == para_start else False
                cont = ts
                break
            pi += 1; cont = None
        return placed, fns, pi, cont, no

    def draw_page(self, page, placed, fns, pageno=None):
        tw = pymupdf.TextWriter(page.rect)
        if pageno:
            center(tw, str(pageno), 36.51 + asc(12), 12)
        for kind, obj, yy, extra in placed:
            if kind == 'h1':
                _tot = measure(obj)
                _x = LEFT + max(0.0, (TEXT_W - _tot) / 2)
                line_out(tw, obj, _x, yy, TEXT_W, False, BODY, True)
            elif kind in ('h2', 'h3'):
                line_out(tw, obj, LEFT + IND, yy, TEXT_W - IND, False, BODY, True)
            elif kind == 'item':
                no, lastline = extra
                if no is not None:
                    put(tw, '%d.' % no, LEFT + 12.0, yy)
                line_out(tw, obj, LEFT + 36.0, yy, TEXT_W - 36.0, False)
            else:
                ind, lastline = extra
                line_out(tw, obj, LEFT + ind, yy, TEXT_W - ind, not lastline)
        ysep = []
        first_top = 0.0
        if fns:
            n = sum(len(foot_lines(t)) for _, t, _g in fns)
            first_top = FN_BOT - (n - 1) * FLH - asc(FOOT)
            ysep.append(first_top - SEP_DY)
        draw_foot(tw, fns, first_top)
        tw.write_text(page)
        for y in ysep:
            page.draw_line((LEFT, y), (LEFT + 144.0, y), width=0.5, color=(0, 0, 0))

    def render(self, out, toc_pages, stats=None):
        items = self.blocks['items']
        pi, cont, y = 0, None, H1TOP + asc(BODY)
        page_no = 3
        page = self.doc.new_page(width=PW, height=PH)
        while True:
            no0 = self.blocks['item_no']
            FNMAP.clear()
            placed, fns, npi, ncont, nno = self.layout(pi, cont, y)
            # номера сносок на странице уточняются до совпадения ширины и отрисовки
            for _ in range(4):
                m = {g: i + 1 for i, (n, txt, g) in enumerate(fns)}
                if m == FNMAP:
                    break
                FNMAP.clear()
                FNMAP.update(m)
                self.blocks['item_no'] = no0
                placed, fns, npi, ncont, nno = self.layout(pi, cont, y)
            # если сносок нет — страницу можно заполнить до низа
            self.draw_page(page, placed, fns, page_no)
            self.blocks['item_no'] = nno
            if npi >= len(items) and ncont is None:
                break
            pi, cont = npi, ncont
            page_no += 1
            page = self.doc.new_page(width=PW, height=PH)
            y = H1TOP + asc(BODY)
        try:
            self.doc.subset_fonts()
        except Exception:
            pass
        self.doc.save(out, deflate=True, garbage=4, clean=True)
        return self.doc.page_count

    def run(self, toc_pages, out):
        self.blocks['item_no'] = 1
        self.title_page()
        self.toc_page(toc_pages, 2)
        return self.render(out, toc_pages)


def make(blocks, title, out, toc_pages=None, stats=None):
    return Builder(blocks, title).run(toc_pages or {}, out)
