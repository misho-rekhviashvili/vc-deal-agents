#!/usr/bin/env python3
"""Ingest a virtual data room (VDR) into a deal folder.

Usage: python3 -I scripts/ingest.py <dataroom_dir> <deal_dir>

Never modifies the data room. Writes:
  <deal_dir>/00-text/D###.md   text extract per document (docx, pptx, xlsx/xlsm, csv, txt, md, doc)
  <deal_dir>/00-manifest.md    one row per document, with ID, folder, type, size and where to read it

PDFs are converted with pdftotext (with "--- page N ---" markers) when poppler is installed
(brew install poppler). Otherwise, and for images and scans, the manifest records the page
count and original path, and agents read the original with the Read tool.
Standard library only.
"""
import csv
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
S = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PR = '{http://schemas.openxmlformats.org/package/2006/relationships}'

MAX_ROWS_PER_SHEET = 400
MAX_COLS = 40
SKIP_NAMES = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}
CONVERT = {'.docx', '.pptx', '.xlsx', '.xlsm', '.csv', '.txt', '.md', '.doc', '.rtf'}
READ_DIRECT = {'.pdf', '.png', '.jpg', '.jpeg', '.gif', '.webp'}


def docx_text(path):
    root = ET.fromstring(zipfile.ZipFile(path).read('word/document.xml'))
    body = root.find(W + 'body')
    out = []

    def para(p):
        t = ''.join(x.text or '' for x in p.iter(W + 't'))
        if not t.strip():
            return None
        sty = p.find(f'{W}pPr/{W}pStyle')
        s = sty.get(W + 'val') if sty is not None else ''
        if s.lower().startswith('heading') or s.lower() == 'title':
            return '## ' + t
        return t

    for child in body:
        if child.tag == W + 'p':
            t = para(child)
            if t:
                out.append(t)
        elif child.tag == W + 'tbl':
            out.append('')
            for tr in child.iter(W + 'tr'):
                cells = [' '.join(filter(None, (para(p) for p in tc.iter(W + 'p')))) for tc in tr.iter(W + 'tc')]
                out.append('| ' + ' | '.join(c.replace('|', '/') for c in cells) + ' |')
            out.append('')
    return '\n'.join(out)


def pptx_text(path):
    z = zipfile.ZipFile(path)
    slides = sorted((n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)),
                    key=lambda n: int(re.findall(r'\d+', n)[0]))
    out = []
    for n in slides:
        out.append(f'\n### Slide {re.findall(r"[0-9]+", n)[0]}')
        root = ET.fromstring(z.read(n))
        in_table = set()
        for tbl in root.iter(A + 'tbl'):
            for p in tbl.iter(A + 'p'):
                in_table.add(id(p))
        for el in root.iter():
            if el.tag == A + 'tbl':
                for tr in el.iter(A + 'tr'):
                    cells = [''.join(t.text or '' for t in tc.iter(A + 't')) for tc in tr.iter(A + 'tc')]
                    out.append('| ' + ' | '.join(c.replace('|', '/') for c in cells) + ' |')
            elif el.tag == A + 'p' and id(el) not in in_table:
                t = ''.join(x.text or '' for x in el.iter(A + 't'))
                if t.strip():
                    out.append(t)
    return '\n'.join(out), len(slides)


def col_letters(ref):
    return re.match(r'[A-Z]+', ref).group(0)


def col_index(letters):
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n


def fmt_num(v):
    try:
        f = float(v)
    except ValueError:
        return v
    if f.is_integer() and abs(f) < 1e15:
        return str(int(f))
    return f'{f:.4g}' if abs(f) < 1 else f'{f:,.2f}'.replace(',', '')


def xlsx_text(path):
    z = zipfile.ZipFile(path)
    shared = []
    if 'xl/sharedStrings.xml' in z.namelist():
        for si in ET.fromstring(z.read('xl/sharedStrings.xml')).iter(S + 'si'):
            shared.append(''.join(t.text or '' for t in si.iter(S + 't')))
    wb = ET.fromstring(z.read('xl/workbook.xml'))
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')).iter(PR + 'Relationship')}
    out, names = [], []
    for sh in wb.iter(S + 'sheet'):
        name = sh.get('name')
        names.append(name)
        target = rels[sh.get(R + 'id')].lstrip('/')
        target = target if target.startswith('xl/') else 'xl/' + target
        out.append(f'\n### Sheet: {name}')
        try:
            root = ET.fromstring(z.read(target))
        except KeyError:
            out.append('(sheet file missing)')
            continue
        rows = list(root.iter(S + 'row'))
        written = 0
        for row in rows:
            cells = []
            for c in row.iter(S + 'c'):
                ref = c.get('r')
                if col_index(col_letters(ref)) > MAX_COLS:
                    continue
                t = c.get('t')
                v = c.find(S + 'v')
                if t == 's' and v is not None:
                    val = shared[int(v.text)]
                elif t == 'inlineStr':
                    val = ''.join(x.text or '' for x in c.iter(S + 't'))
                elif v is not None and v.text is not None:
                    val = v.text if t in ('str', 'e') else fmt_num(v.text)
                else:
                    continue
                val = val.strip().replace('\n', ' ')
                if val:
                    cells.append(f'{col_letters(ref)}={val}')
            if cells:
                out.append(f'R{row.get("r")}: ' + ' | '.join(cells))
                written += 1
                if written >= MAX_ROWS_PER_SHEET:
                    out.append(f'(truncated after {MAX_ROWS_PER_SHEET} non-empty rows; open the original file for the rest)')
                    break
    return '\n'.join(out), names


def pdf_pages(path):
    try:
        r = subprocess.run(['mdls', '-raw', '-name', 'kMDItemNumberOfPages', path], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() if r.stdout.strip().isdigit() else '?'
    except Exception:
        return '?'


def main(dataroom, deal_dir):
    dataroom = os.path.abspath(dataroom)
    text_dir = os.path.join(deal_dir, '00-text')
    os.makedirs(text_dir, exist_ok=True)
    files = []
    for dirpath, dirnames, filenames in os.walk(dataroom):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith('.'))
        for f in sorted(filenames):
            if f in SKIP_NAMES or f.startswith('.~lock') or f.startswith('~$') or f.startswith('.'):
                continue
            files.append(os.path.join(dirpath, f))

    rows = []
    for i, path in enumerate(files, 1):
        did = f'D{i:03d}'
        rel = os.path.relpath(path, dataroom)
        folder = os.path.dirname(rel) or '(root)'
        ext = os.path.splitext(path)[1].lower()
        size_kb = max(1, os.path.getsize(path) // 1024)
        detail, read_at, err = '', '', ''
        text = None
        try:
            if ext == '.docx':
                text = docx_text(path)
            elif ext == '.pptx':
                text, n = pptx_text(path)
                detail = f'{n} slides'
            elif ext in ('.xlsx', '.xlsm'):
                text, names = xlsx_text(path)
                detail = f'{len(names)} sheets: ' + ', '.join(names)[:120]
            elif ext == '.csv':
                with open(path, newline='', encoding='utf-8', errors='replace') as fh:
                    text = '\n'.join(' | '.join(r) for r in csv.reader(fh))
            elif ext in ('.txt', '.md'):
                with open(path, encoding='utf-8', errors='replace') as fh:
                    text = fh.read()
            elif ext in ('.doc', '.rtf'):
                r = subprocess.run(['textutil', '-convert', 'txt', '-stdout', path], capture_output=True, text=True, timeout=60)
                text = r.stdout
            elif ext == '.pdf':
                detail = f'{pdf_pages(path)} pages'
                read_at = path
                if shutil.which('pdftotext'):
                    r = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, timeout=300)
                    pages = r.stdout.split('\f')
                    if sum(len(p.strip()) for p in pages) > 200:  # skip scans with no text layer
                        text = '\n'.join(f'\n--- page {i} ---\n{p}' for i, p in enumerate(pages, 1) if p.strip())
                    else:
                        err = 'no text layer (scanned): read original'
            elif ext in READ_DIRECT:
                detail = 'image'
                read_at = path
            else:
                err = 'unsupported type: open manually'
        except Exception as e:  # corrupt or password protected files
            err = f'extraction failed ({type(e).__name__}): read original'
            read_at = path
        if text is not None:
            out_path = os.path.join(text_dir, f'{did}.md')
            with open(out_path, 'w', encoding='utf-8') as fh:
                fh.write(f'# {did}: {os.path.basename(path)}\n\nSOURCE: {path}\nFOLDER: {folder}\n\n{text}\n')
            read_at = os.path.relpath(out_path, deal_dir)
            detail = (detail + '; ' if detail else '') + f'{len(text):,} chars'
        rows.append((did, folder, os.path.basename(path), ext.lstrip('.') or '?', size_kb, detail, read_at, err))

    with open(os.path.join(deal_dir, '00-manifest.md'), 'w', encoding='utf-8') as fh:
        fh.write(f'# Data room manifest\n\nDATA ROOM: {dataroom}\nDOCUMENTS: {len(rows)}\n\n')
        fh.write('| ID | Folder | File | Type | KB | Detail | Read at | Note |\n|---|---|---|---|---|---|---|---|\n')
        for r in rows:
            fh.write('| ' + ' | '.join(str(x).replace('|', '/') for x in r) + ' |\n')
    converted = sum(1 for r in rows if r[6].startswith('00-text'))
    direct = sum(1 for r in rows if r[6] and not r[6].startswith('00-text') and not r[7])
    failed = sum(1 for r in rows if r[7])
    print(f'{len(rows)} documents: {converted} converted to text, {direct} PDFs/images to read directly, {failed} need attention')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
