# -*- coding: utf-8 -*-
"""Комплексный аудит текста курсовой работы БЮИ на ИИ-паттерны, ритм, структуру, сноски и оформление.

Проверяет исходные файлы src/01.txt..05.txt без внешних зависимостей (чистый Python 3 stdlib).
Объединяет критерии руководства от 22.10.2026 и доработок из проходов 30.10–11.11.2026.

Пример:
  python3 pipeline/audit_metrics.py works/07_terroristicheskiy_akt_205/src
"""
import argparse
import glob
import json
import os
import re
import statistics
import sys

COLLOQUIAL_PATTERNS = [
    r'\bбыту(?:ет|ют)\b',
    r'\bбь[её]т\s+по\b',
    r'\bцена\s+ошибк\w*\b',
    r'\bсто[ия]т\s+дорог\w*\b',
    r'\bневооруж[её]нным\s+глазом\b',
    r'\bдело\s+доходит\b',
    r'\bвскрыва(?:ет|ют)\b',
    r'\bпутаниц\w*\b',
    r'\bпиш(?:ет|ут)\s+прямо\b',
    r'\bвиден\s+в\s+чистом\s+виде\b',
    r'\bоборачива(?:ет|ют)ся\b',
    r'\bзадева(?:ет|ют)\b',
    r'\bвесит\s+больше\b',
    r'\bпрост(?:ой|ое|ая)\s+(?:вывод|пример)\b',
]

NEGATIVE_CLAIM_PATTERNS = [
    r'\b(?:закон|кодекс|пленум|постановление|практика)\s+не\s+(?:решает|разъясняет|знает|содержит|устанавливает|предусматривает|отвечает)\b',
    r'\bни\s+(?:один|одна|одно)\s+(?:автор|суд|постановление|норма)\b',
    r'\bв\s+(?:литературе|науке|практике)\s+не\s+(?:встречается|рассматривается|сложилось|выработано)\b',
    r'\b(?:особого|повышенного)\s+внимания\s+судов\b',
]

ABBR = {
    'г', 'гг', 'в', 'вв', 'п', 'пп', 'ст', 'ч', 'с', 'см', 'др', 'ред',
    'напр', 'д', 'т', '№', 'тыс', 'млн', 'млрд', 'руб', 'проц', 'абз', 'подп', 'утв',
}

CLICHES = [
    ('таким образом', r'\bтаким\s+образом\b'),
    ('следовательно', r'\bследовательно\b'),
    ('кроме того', r'\bкроме\s+того\b'),
    ('вместе с тем', r'\bвместе\s+с\s+тем\b'),
    ('при этом', r'\bпри\s+этом\b'),
    ('более того', r'\bболее\s+того\b'),
    ('помимо этого / того', r'\bпомимо\s+(?:этого|того)\b'),
    ('следует отметить', r'\bследует\s+(?:отметить|подчеркнуть|указать|сказать)\b'),
    ('необходимо отметить/подчеркнуть', r'\bнеобходимо\s+(?:отметить|подчеркнуть|указать|выделить)\b'),
    ('важно отметить/понимать', r'\bважно\s+(?:отметить|подчеркнуть|понимать|учитывать)\b'),
    ('стоит отметить/указать', r'\bстоит\s+(?:отметить|подчеркнуть|указать|обратить\s+внимание)\b'),
    ('нельзя не отметить', r'\bнельзя\s+не\s+(?:отметить|признать|согласиться)\b'),
    ('обобщая / резюмируя', r'\b(?:обобщая|резюмируя|подводя\s+итог)\b'),
    ('заслуживает внимания', r'\bзаслуживает\s+(?:внимания|особого\s+внимания)\b'),
    ('представляется возможным/целесообразным', r'\bпредставляется\s+(?:возможным|целесообразным|очевидным|важным)\b'),
    ('на сегодняшний день / в современных условиях', r'\b(?:на\s+сегодняшний\s+день|в\s+современных\s+условиях|в\s+настоящее\s+время|в\s+условиях\s+современности)\b'),
    ('играет важную/ключевую роль', r'\bигра(?:ет|ют)\s+(?:важную|ключевую|особую|существенную|значительную)\s+роль\b'),
    ('в рамках', r'\bв\s+рамках\b'),
    ('является / являются', r'\bявля(?:ет|ют)ся\b'),
    ('представляет собой', r'\bпредставля(?:ет|ют)\s+собой\b'),
    ('однако', r'\bоднако\b'),
    ('данный/данные (канц.)', r'\bданн(?:ый|ая|ое|ые|ого|ой|ому|ым|ом|ых)\b'),
    ('именно (усил.)', r'\bименно\b'),
    ('достаточно (размыт.)', r'\bдостаточно\b'),
    ('также', r'\bтакже\b'),
    ('очевидно / безусловно / несомненно', r'\b(?:очевидно|безусловно|несомненно)\b'),
    ('вывод по параграфу/главе', r'\bвывод(?:ы)?\s+по\s+(?:параграфу|главе)\b'),
    ('по N-й задаче', r'\bпо\s+(?:первой|второй|третьей|четвёртой|четвертой|пятой)\s+задаче\b'),
    ('не только ..., но и ...', r'\bне\s+только\b[^.!?]{0,120}\bно\s+и\b'),
    ('не X, а Y (шаблон контраста)', r'\bне\s+[а-яё\-]{3,25},\s+а\s+[а-яё\-]{3,25}\b'),
    ('во-первых / во-вторых / в-третьих', r'\bво-(?:первых|вторых)|в-третьих\b'),
    ('N-й признак / элемент', r'\b(?:первый|второй|третий|четвёртый|четвертый|пятый)\s+(?:признак|элемент|аспект|фактор)\b'),
    ('отсюда следует', r'\bотсюда\s+следует\b'),
    ('показывает (речевой штамп)', r'\bпоказыва(?:ет|ют)\b'),
]


def load_sections(src_dir):
    files = sorted(glob.glob(os.path.join(src_dir, '0*.txt')))
    if not files:
        raise FileNotFoundError(f'Файлы 0*.txt не найдены в {src_dir}')
    parsed = []
    for path in files:
        fname = os.path.basename(path)
        with open(path, encoding='utf-8') as fh:
            for lineno, raw in enumerate(fh, 1):
                s = raw.rstrip('\n')
                if not s.strip():
                    continue
                if s.startswith(('H1 ', 'H2 ', 'H3 ', 'L ')):
                    kind = s[:2].strip() if not s.startswith('L ') else 'L'
                    parsed.append((fname, lineno, kind, s[len(kind) + 1:].strip()))
                else:
                    parsed.append((fname, lineno, 'P', s.strip()))
    return parsed


def split_sentences(txt):
    t = re.sub(r'\s+', ' ', txt).strip()
    res, start = [], 0
    for m in re.finditer(r'[.!?](?=\s+[А-ЯЁ«"(])', t):
        prev = t[max(0, m.start() - 12):m.start() + 1].split()
        last = prev[-1].rstrip('.').lower() if prev else ''
        year = bool(re.search(r'\d{4}\s+г$', t[max(0, m.start() - 9):m.start()]))
        if last == 'г' and year:
            pass
        elif last in ABBR or re.fullmatch(r'[а-яё]', last) or re.fullmatch(r'\d+', last):
            continue
        res.append(t[start:m.end()].strip())
        start = m.end()
    if start < len(t):
        res.append(t[start:].strip())
    return [s for s in res if s]


def words_only(txt):
    return re.findall(r'[А-Яа-яЁёA-Za-z]+', txt)


def strip_fn(txt):
    return re.sub(r'\[\[fn:.*?\]\]', '', txt, flags=re.S).strip()


def run_audit(src_dir):
    blocks = load_sections(src_dir)

    body_blocks = []
    bib_blocks = []
    headings = []
    in_bib = False
    for fname, lineno, kind, text in blocks:
        if kind == 'H1' and text.startswith('СПИСОК'):
            in_bib = True
        if kind in ('H1', 'H2', 'H3'):
            headings.append((fname, lineno, kind, text, in_bib))
        elif in_bib:
            bib_blocks.append((fname, lineno, kind, text))
        else:
            body_blocks.append((fname, lineno, kind, text))

    # --- 1. Метрики предложений ---
    body_clean_paras = [(fn, ln, strip_fn(t)) for fn, ln, _, t in body_blocks]
    full_body = '\n'.join(t for _, _, t in body_clean_paras if t)
    sents = split_sentences(full_body)
    s_lens = [len(words_only(s)) for s in sents if words_only(s)]
    all_words = words_only(full_body)
    lemmas_approx = [w.lower().replace('ё', 'е') for w in all_words]
    ttr = round(len(set(lemmas_approx)) / max(1, len(lemmas_approx)), 3)
    cv = round(statistics.pstdev(s_lens) / max(0.01, statistics.mean(s_lens)), 2) if len(s_lens) > 1 else 0.0

    # Серии из 3+ предложений подряд почти равной длины (+-2 слова)
    flat_runs = []
    cur = 0
    while cur < len(s_lens):
        end = cur + 1
        while end < len(s_lens) and max(s_lens[cur:end + 1]) - min(s_lens[cur:end + 1]) <= 2:
            end += 1
        if end - cur >= 3:
            flat_runs.append({'start_idx': cur, 'count': end - cur, 'lengths': s_lens[cur:end],
                              'sample': sents[cur][:90]})
        cur = end if end > cur + 1 else cur + 1

    # --- 2. Метрики абзацев ---
    p_lens = [len(words_only(t)) for _, _, t in body_clean_paras if words_only(t)]
    p_med = statistics.median(p_lens) if p_lens else 0
    long_paras = [{'file': fn, 'line': ln, 'words': len(words_only(t)), 'head': t[:80]}
                  for fn, ln, t in body_clean_paras if len(words_only(t)) > max(120, 2 * p_med)]
    stub_paras = [{'file': fn, 'line': ln, 'words': len(words_only(t)), 'text': t}
                  for fn, ln, t in body_clean_paras if 0 < len(words_only(t)) < 22]

    # Повторы зачинов абзацев (первые 1, 2 и 3 слова)
    open1, open2, open3 = {}, {}, {}
    adj_openers = []
    prev_first = None
    for fn, ln, t in body_clean_paras:
        ws = [w.lower() for w in words_only(t)]
        if not ws:
            continue
        k1, k2, k3 = ws[0], ' '.join(ws[:2]), ' '.join(ws[:3])
        open1.setdefault(k1, []).append(f'{fn}:{ln}')
        if len(ws) >= 2:
            open2.setdefault(k2, []).append(f'{fn}:{ln}')
        if len(ws) >= 3:
            open3.setdefault(k3, []).append(f'{fn}:{ln}')
        if prev_first and prev_first[0] == k1 and len(k1) > 2:
            adj_openers.append({'word': k1, 'prev': prev_first[1], 'curr': f'{fn}:{ln}'})
        prev_first = (k1, f'{fn}:{ln}')

    rep_open2 = {k: v for k, v in open2.items() if len(v) >= 2}
    rep_open3 = {k: v for k, v in open3.items() if len(v) >= 2}

    # --- 3. ИИ-клише и триады ---
    cliche_hits = {}
    for label, pat in CLICHES:
        matches = re.findall(pat, full_body, flags=re.I)
        if matches:
            cliche_hits[label] = len(matches)
    triads = re.findall(r'\b[А-Яа-яЁё\-]{3,},\s+[А-Яа-яЁё\-]{3,}\s+и\s+[А-Яа-яЁё\-]{3,}\b', full_body)

    # Разговорные обороты и неподтверждённые отрицательные/оценочные утверждения
    colloquial_hits = []
    for pat in COLLOQUIAL_PATTERNS:
        for m in re.finditer(pat, full_body, flags=re.I):
            colloquial_hits.append(m.group(0))

    negative_claims = []
    for pat in NEGATIVE_CLAIM_PATTERNS:
        for m in re.finditer(pat, full_body, flags=re.I):
            negative_claims.append(full_body[max(0, m.start() - 25):m.end() + 45].replace('\n', ' '))

    # Повтор одинакового первого слова у соседних предложений в одном абзаце
    para_sent_repeats = []
    for fn, ln, t in body_clean_paras:
        ps = split_sentences(t)
        firsts = [words_only(s)[0].lower() for s in ps if words_only(s)]
        for idx in range(len(firsts) - 1):
            if firsts[idx] == firsts[idx + 1] and len(firsts[idx]) > 2:
                para_sent_repeats.append(f'{fn}:{ln} («{firsts[idx]}»)')

    # --- 4. Типографика и сноски ---
    raw_all_body = '\n'.join(t for _, _, _, t in body_blocks)
    raw_all = raw_all_body + '\n' + '\n'.join(t for _, _, _, t in bib_blocks)
    long_dashes = raw_all.count('—')
    straight_quotes = raw_all.count('"')
    double_spaces = len(re.findall(r'  +', raw_all))
    double_dots_fn = len(re.findall(r'г\.\[\[fn:[^\]]+\]\]\.', raw_all_body))
    unclosed_fn = raw_all_body.count('[[fn:') != raw_all_body.count(']]')

    fn_texts = re.findall(r'\[\[fn:(.*?)\]\]', raw_all_body, flags=re.S)
    fn_tamzhe = [i + 1 for i, f in enumerate(fn_texts) if re.search(r'\b(?:там\s+же|указ\.?\s*соч)\b', f, flags=re.I)]
    fn_with_url = [i + 1 for i, f in enumerate(fn_texts) if re.search(r'(?:URL:|https?://)', f, flags=re.I)]
    fn_sm = [i + 1 for i, f in enumerate(fn_texts) if re.search(r'\bсм\.?:', f, flags=re.I)]

    # --- 5. Заголовки и структура ---
    heading_issues = []
    h1_texts, h2_texts = [], []
    for fn, ln, kind, text, in_b in headings:
        if kind == 'H1' and not text.isupper():
            heading_issues.append(f'{fn}:{ln} H1 не ПРОПИСНЫМИ: {text}')
        if text.endswith('.'):
            heading_issues.append(f'{fn}:{ln} точка в конце заголовка: {text}')
        if kind == 'H1' and not in_b:
            h1_texts.append(text)
        elif kind == 'H2' and not in_b:
            h2_texts.append(text)

    # Разбор разделов списка источников (H2/H3 после H1 СПИСОК...)
    sec_items = {}
    in_bib_sec = False
    cur_bib_sec = None
    for fn, ln, kind, text in blocks:
        if kind == 'H1' and text.startswith('СПИСОК'):
            in_bib_sec = True
            cur_bib_sec = None
        elif in_bib_sec:
            if kind in ('H2', 'H3'):
                cur_bib_sec = text
                sec_items.setdefault(cur_bib_sec, [])
            elif kind == 'L' and cur_bib_sec:
                sec_items.setdefault(cur_bib_sec, []).append((ln, text))

    bib_order_warnings = []
    if len(sec_items) != 3:
        bib_order_warnings.append(f'В списке должно быть 3 подраздела (НПА, Литература, Эмпирика), найдено: {len(sec_items)}')
    for sec, items in sec_items.items():
        if re.search(r'литератур|эмпирич', sec, flags=re.I):
            def _bib_key(text_item):
                s = re.sub(r'[^а-яёa-z0-9 ]', '', text_item.lower()).strip()
                is_lat = 1 if (s and 'a' <= s[0] <= 'z') else 0
                return (is_lat, s)
            keys = [_bib_key(it) for _, it in items]
            for idx in range(len(keys) - 1):
                if keys[idx] > keys[idx + 1]:
                    bib_order_warnings.append(
                        f'Нарушен алфавит в «{sec}»: «{items[idx][1][:45]}» перед «{items[idx + 1][1][:45]}»'
                    )
        for ln, it in items:
            if not it.endswith('.'):
                bib_order_warnings.append(f'05.txt:{ln} запись списка без точки в конце: «{it[:50]}»')
            if 'URL:' in it and 'дата обращения:' not in it:
                bib_order_warnings.append(f'05.txt:{ln} есть URL без «(дата обращения: ...)»: «{it[:50]}»')

    report = {
        'src_dir': os.path.abspath(src_dir),
        'volume': {
            'body_words': len(all_words),
            'body_chars_no_fn': len(full_body),
            'paragraphs': len(p_lens),
            'sentences': len(s_lens),
            'footnotes': len(fn_texts),
            'bib_items': sum(len(v) for v in sec_items.values()),
            'bib_sections': {k: len(v) for k, v in sec_items.items()},
        },
        'rhythm_and_variety': {
            'sent_mean_words': round(statistics.mean(s_lens), 2) if s_lens else 0,
            'sent_median_words': statistics.median(s_lens) if s_lens else 0,
            'sent_cv_target_ge_0_48': cv,
            'pct_short_lt_8_target_ge_20': round(100 * sum(1 for x in s_lens if x < 8) / max(1, len(s_lens)), 1),
            'sents_gt_30_words': sum(1 for x in s_lens if x > 30),
            'sents_gt_40_words': sum(1 for x in s_lens if x > 40),
            'sent_max_words': max(s_lens) if s_lens else 0,
            'flat_runs_3plus_equal_len_sents': flat_runs,
            'para_median_words': p_med,
            'para_min_max_words': [min(p_lens), max(p_lens)] if p_lens else [0, 0],
            'ttr_approx': ttr,
        },
        'structural_flags': {
            'adjacent_same_first_word': adj_openers,
            'repeated_2word_para_openers': rep_open2,
            'repeated_3word_para_openers': rep_open3,
            'repeated_sent_openers_in_para': para_sent_repeats,
            'long_paras_gt_2x_median': long_paras,
            'stub_paras_lt_22_words': stub_paras,
        },
        'ai_cliche_counts': cliche_hits,
        'triads_A_B_and_C_count': len(triads),
        'colloquial_hits': colloquial_hits,
        'negative_claims_to_verify': negative_claims,
        'formatting_and_citations': {
            'long_dashes_must_be_0': long_dashes,
            'straight_quotes_must_be_0': straight_quotes,
            'double_spaces_must_be_0': double_spaces,
            'double_dot_after_g_fn': double_dots_fn,
            'unclosed_fn_brackets': unclosed_fn,
            'fn_tamzhe_or_ukaz_soch': fn_tamzhe,
            'fn_leaked_url': fn_with_url,
            'fn_with_sm': fn_sm,
            'heading_issues': heading_issues,
            'bib_order_warnings': bib_order_warnings,
        },
    }
    return report


def main():
    ap = argparse.ArgumentParser(description='Аудит текста курсовой (0*.txt) на ИИ-паттерны и соответствие БЮИ')
    ap.add_argument('src_dir', help='Каталог с файлами 01.txt..05.txt')
    args = ap.parse_args()
    rep = run_audit(args.src_dir)
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
