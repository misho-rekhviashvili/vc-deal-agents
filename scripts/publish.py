#!/usr/bin/env python3
"""Publish the clean deliverables once QC passes.

Usage: python3 -I scripts/publish.py <deal_dir> <memo.md> <one-pager.md>

Copies the final memo, the one-pager, the IC prep questions and the data request list into
<deal_dir>/final/, stripping internal reference tags ([F-07], [E-02], [R-01], [FIN-03, D012 p.4]).
Refuses to overwrite an existing final/ folder.
"""
import os
import re
import sys

TAGS = re.compile(r'\s?\[(?:[A-Z]{1,4}-\d+|D\d{3})[^\]]*\]')


def clean(src, dst):
    text = open(src, encoding='utf-8').read()
    text = TAGS.sub('', text)
    with open(dst, 'w', encoding='utf-8') as fh:
        fh.write(text)
    print(f'wrote {dst}')


def section(src, heading):
    """Return the text under a '## heading' up to the next '## '."""
    text = open(src, encoding='utf-8').read()
    m = re.search(rf'^## {re.escape(heading)}.*?$(.*?)(?=^## |\Z)', text, re.S | re.M)
    return m.group(1).strip() if m else ''


def main(deal_dir, memo, one_pager):
    final = os.path.join(deal_dir, 'final')
    if os.path.exists(final):
        sys.exit(f'{final} already exists: never overwrite a published run')
    os.makedirs(final)
    clean(memo, os.path.join(final, 'IC-Memo.md'))
    clean(one_pager, os.path.join(final, 'One-Pager.md'))
    reviews = sorted(f for f in os.listdir(deal_dir) if f.startswith('06-ic-review'))
    if reviews:
        qa = section(os.path.join(deal_dir, reviews[-1]), 'IC PREP QUESTIONS')
        with open(os.path.join(final, 'IC-Prep-Questions.md'), 'w', encoding='utf-8') as fh:
            fh.write('# IC preparation: anticipated questions\n\n' + TAGS.sub('', qa) + '\n')
        print(f'wrote {final}/IC-Prep-Questions.md')
    findings = os.path.join(deal_dir, '02-key-findings.md')
    if os.path.exists(findings):
        dr = section(findings, 'DATA REQUEST LIST')
        with open(os.path.join(final, 'Data-Request.md'), 'w', encoding='utf-8') as fh:
            fh.write('# Data request list\n\n' + TAGS.sub('', dr) + '\n')
        print(f'wrote {final}/Data-Request.md')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    main(*sys.argv[1:])
