"""Fix broken Unicode symbols in PROJECT_SUMMARY.md."""

REPLACEMENTS = [
    # Unicode replacement chars from bad encoding
    ('\ufffd', ''),
    # Corrupted Greek capital gamma (from git show UTF-16 bleed)
    ('\u0393', ''),
    # Smart quotes -> regular quotes
    ('\u201c', '"'), ('\u201d', '"'),
    ('\u2018', "'"), ('\u2019', "'"),
    # Em dash -> hyphen
    ('\u2014', '--'),
    # En dash -> hyphen
    ('\u2013', '-'),
    # Corrupted arrow sequences that come through as ?
    # These are the ones git show wrote wrong; replace with ASCII equivalents
    ('\u2192', '->'),   # ->
    ('\u2190', '<-'),
    ('\u2713', '[OK]'), # checkmark
    ('\u2714', '[OK]'),
    # Box-drawing chars that render badly on some viewers - keep them, they're fine in markdown
]

def fix_file(path: str):
    with open(path, 'rb') as f:
        raw = f.read()

    # Detect encoding
    if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
        content = raw.decode('utf-16')
    else:
        content = raw.decode('utf-8', errors='replace')

    original = content
    for bad, good in REPLACEMENTS:
        content = content.replace(bad, good)

    changed = sum(1 for a, b in zip(original.splitlines(), content.splitlines()) if a != b)
    print(f"Lines changed: {changed}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Fixed and saved as UTF-8: {path}")

if __name__ == '__main__':
    fix_file('PROJECT_SUMMARY.md')
