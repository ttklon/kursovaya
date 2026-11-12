# -*- coding: utf-8 -*-
"""Проверка антиплагиата по 8-граммам: против скачанных источников И против прошлых курсовых работ.

Пример:
  python3 pipeline/audit_ngrams.py \\
    --src works/04_ugolovnyy_zakon/src \\
    --sources works/04_ugolovnyy_zakon/sources \\
    --compare-works works
"""
import argparse
import glob
import html
import os
import re
import json


def clean_text(raw):
    raw = re.sub(r'(?is)<(script|style)[^>]*>.*?</\1>', ' ', raw)
    raw = re.sub(r'(?s)<[^>]+>', ' ', raw)
    return html.unescape(raw)


def tokenize(txt):
    return re.findall(r'[а-яёa-z0-9]+', txt.lower().replace('ё', 'е'))


def collect_tokens(root_dir, exclude_dir=None, n=8):
    grams = {}
    excl = os.path.abspath(exclude_dir) if exclude_dir else None
    total_tokens = 0
    files_read = 0
    for dirpath, _, filenames in os.walk(root_dir):
        if excl and os.path.abspath(dirpath).startswith(excl):
            continue
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in ('.txt', '.html', '.htm'):
                continue
            p = os.path.join(dirpath, fn)
            raw = open(p, encoding='utf-8', errors='replace').read()
            if ext in ('.html', '.htm'):
                raw = clean_text(raw)
            else:
                raw = re.sub(r'\[\[fn:.*?\]\]', '', raw, flags=re.S)
                raw = '\n'.join(ln for ln in raw.splitlines() if not re.match(r'^(?:H[123]|L)\s', ln))
            toks = tokenize(raw)
            total_tokens += len(toks)
            files_read += 1
            rel = os.path.relpath(p, root_dir)
            for i in range(max(0, len(toks) - n + 1)):
                g = tuple(toks[i:i + n])
                grams.setdefault(g, rel)
    return grams, total_tokens, files_read


def audit_target(src_dir, corpus_grams, n=8):
    body = []
    for p in sorted(glob.glob(os.path.join(src_dir, '0[1-4]*.txt'))):
        for ln in open(p, encoding='utf-8'):
            if re.match(r'^H[123]\s', ln):
                continue
            body.append(re.sub(r'\[\[fn:.*?\]\]', '', ln, flags=re.S))
    B = tokenize(' '.join(body))
    windows = max(1, len(B) - n + 1)
    hits = [i for i in range(len(B) - n + 1) if tuple(B[i:i + n]) in corpus_grams]
    spans = []
    i_idx = 0
    while i_idx < len(hits):
        start = hits[i_idx]
        end = start + n
        src_file = corpus_grams[tuple(B[start:end])]
        while i_idx + 1 < len(hits) and hits[i_idx + 1] <= end:
            i_idx += 1
            end = hits[i_idx] + n
        spans.append({
            'words': end - start,
            'source': src_file,
            'fragment': ' '.join(B[start:end])[:220],
        })
        i_idx += 1
    spans.sort(key=lambda x: -x['words'])
    return {
        'body_words': len(B),
        'matched_windows': len(hits),
        'overlap_pct': round(100.0 * len(hits) / windows, 2),
        'longest_span_words': spans[0]['words'] if spans else 0,
        'top_matches': spans[:15],
    }


def main():
    ap = argparse.ArgumentParser(description='Проверка 8-грамм против источников и прошлых работ')
    ap.add_argument('--src', required=True, help='Каталог с файлами 01..04.txt проверяемой работы')
    ap.add_argument('--sources', nargs='*', default=[], help='Каталоги со скачанными источниками (.txt/.html)')
    ap.add_argument('--compare-works', default=None, help='Корневой каталог works/ для проверки самозаимствования')
    ap.add_argument('--ngram', type=int, default=8)
    args = ap.parse_args()

    out = {'src': os.path.abspath(args.src), 'ngram': args.ngram}
    if args.sources:
        all_grams = {}
        tot_t, tot_f = 0, 0
        for sd in args.sources:
            g, tt, tf = collect_tokens(sd, n=args.ngram)
            all_grams.update(g)
            tot_t += tt
            tot_f += tf
        res = audit_target(args.src, all_grams, n=args.ngram)
        res.update({'corpus_files': tot_f, 'corpus_words': tot_t})
        out['vs_sources'] = res

    if args.compare_works:
        work_root = os.path.dirname(os.path.abspath(args.src))
        g, tt, tf = collect_tokens(args.compare_works, exclude_dir=work_root, n=args.ngram)
        res = audit_target(args.src, g, n=args.ngram)
        res.update({'other_files': tf, 'other_words': tt})
        out['vs_other_works'] = res

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
