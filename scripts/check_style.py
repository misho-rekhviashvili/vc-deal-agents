#!/usr/bin/env python3
"""House style and traceability lint for the qc-officer agent.

Usage: python3 -I scripts/check_style.py <file.md> [--require-tags]

Checks, line by line:
  HYPHEN   a hyphen or dash used in prose (house rule: use colon or other punctuation).
           Markdown list markers, table rules and reference tags like [F-07] are ignored.
  SALES    promotional words the house style bans
  UNTAGGED (with --require-tags) a line with a figure but no [F-xx]/[E-xx]/[R-xx] tag
Exit code 0 when clean, 1 when anything is flagged.
"""
import re
import sys

BANNED = ['exciting', 'unique opportunity', 'game changer', 'game-changer', 'revolutionary', 'world class',
          'world-class', 'best in class', 'best-in-class', 'incredible', 'massive', 'huge', 'amazing',
          'unparalleled', 'disruptive', 'cutting edge', 'cutting-edge', 'no-brainer', 'once in a lifetime']
TAG = re.compile(r'\[(?:F|E|R)-\d+(?:\s*,\s*(?:F|E|R)-\d+)*\]')
FIGURE = re.compile(r'\d+(?:[.,]\d+)?\s*(?:%|x\b|[MBK]\b|bn\b|m\b)|[€$£]\s?\d')


def main(path, require_tags):
    issues = []
    for n, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.rstrip('\n')
        s = line.strip()
        if not s or re.fullmatch(r'\|?[\s:|-]+\|?', s) or s.startswith('<!--'):
            continue
        body = re.sub(r'^\s*(?:[-*]|\d+\.)\s+', '', line)          # list markers
        body = re.sub(r'\[[A-Z]{1,4}-\d+[^\]]*\]', '', body)       # [F-07], [FIN-03, D012 p.4]
        body = re.sub(r'\bD\d{3}\b', '', body)
        if re.search(r'[-—]', body):
            issues.append((n, 'HYPHEN', s))
        low = body.lower()
        for w in BANNED:
            if w in low:
                issues.append((n, 'SALES', f'"{w}": {s}'))
        if require_tags and FIGURE.search(body) and not TAG.search(line) and not s.startswith(('#', '|')):
            issues.append((n, 'UNTAGGED', s))
    for n, kind, s in issues:
        print(f'{path}:{n}: {kind}: {s[:160]}')
    counts = {k: sum(1 for i in issues if i[1] == k) for k in ('HYPHEN', 'SALES', 'UNTAGGED')}
    print(f'SUMMARY: ' + ', '.join(f'{k} {v}' for k, v in counts.items()))
    return 1 if issues else 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], '--require-tags' in sys.argv))
