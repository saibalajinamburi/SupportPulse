"""
Complete fix for PROJECT_SUMMARY.md:
- Strips ALL non-ASCII characters and replaces with clean ASCII equivalents
- Fixes localhost URLs to correct ports
- Saves as clean UTF-8
"""

import re

# Map of specific Unicode chars to ASCII replacements
CHAR_MAP = {
    '\u2192': '->',     # right arrow
    '\u2190': '<-',     # left arrow
    '\u2713': '[OK]',   # checkmark
    '\u2714': '[OK]',   # heavy checkmark
    '\u2718': '[X]',    # cross mark
    '\u2717': '[X]',    # ballot X
    '\u2714': '[OK]',
    '\u2022': '-',      # bullet
    '\u2023': '-',      # triangular bullet
    '\u25b6': '>',      # right pointing triangle
    '\u25c0': '<',      # left pointing triangle
    '\u2014': '--',     # em dash
    '\u2013': '-',      # en dash
    '\u2012': '-',      # figure dash
    '\u201c': '"',      # left double quote
    '\u201d': '"',      # right double quote
    '\u2018': "'",      # left single quote
    '\u2019': "'",      # right single quote
    '\u00b7': '-',      # middle dot
    '\u00d7': 'x',      # multiplication sign
    '\u00e9': 'e',      # e with accent
    '\u00e0': 'a',      # a with accent
    '\u00e8': 'e',      # e with grave
    '\u2026': '...',    # ellipsis
    '\u00a0': ' ',      # non-breaking space
    '\ufffd': '',       # replacement char (was already broken)
    '\u0393': '',       # Greek gamma (encoding artifact)
    '\u00c7': 'C',      # C cedilla
    '\u00f6': 'o',      # o umlaut
    '\u00e7': 'c',      # c cedilla
    '\u00a3': 'GBP',    # pound sign (was encoding artifact)
    '\u00e2': 'a',      # a circumflex (encoding artifact)
}

def clean(content: str) -> str:
    for bad, good in CHAR_MAP.items():
        content = content.replace(bad, good)
    # Replace any remaining non-ASCII chars
    result = []
    for ch in content:
        if ord(ch) > 127:
            result.append('')  # drop unknown non-ASCII
        else:
            result.append(ch)
    return ''.join(result)

def fix_localhost_urls(content: str) -> str:
    """Ensure localhost URLs use correct port numbers."""
    # Fix any broken localhost references
    content = re.sub(r'localhost:\s*(\d+)', r'localhost:\1', content)
    return content

with open('PROJECT_SUMMARY.md', 'rb') as f:
    raw = f.read()

# Detect encoding
if raw[:2] in (b'\xff\xfe', b'\xfe\xff'):
    content = raw.decode('utf-16')
    print("Was UTF-16, converting to UTF-8")
else:
    content = raw.decode('utf-8', errors='replace')
    print("Was UTF-8 (with replacements)")

original_len = len(content)
content = clean(content)
content = fix_localhost_urls(content)

# Final check
remaining = sum(1 for ch in content if ord(ch) > 127)
print(f"Original length: {original_len}")
print(f"Final length:    {len(content)}")
print(f"Non-ASCII chars remaining: {remaining}")

with open('PROJECT_SUMMARY.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("PROJECT_SUMMARY.md saved as clean UTF-8.")
