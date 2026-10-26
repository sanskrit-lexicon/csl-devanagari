# coding=utf-8
"""Convert Sanskrit text from SLP1 to Devanagari transliteration.
    Author - Dr. Dhaval Patel
    email - drdhaval2785@gmail.com
    date - 03 September 2021
    Usage - python3 to_devanagari.py dictcode
    e.g. - python3 to_devanagari.py mw
"""
import codecs
import sys
import os
import re
from indic_transliteration import sanscript

XML_TAG_RE = re.compile(r'(<[^<>]*>)')

# Only Vedic dictionaries carry svara accent marks; all others use plain SLP1.
ACCENTED_DICTS = {'acc', 'gra'}

# Metaline fields whose values are Sanskrit text; every other field is kept byte
# for byte (numbers, `<pc>`, `<h>` class letters, unknown future tags).
METALINE_TEXT_KEYS = ('k1', 'k2')


def transliterate_text_preserving_xml_tags(text, inputTranslit):
    """Transliterate text nodes while preserving XML-like tags."""
    parts = XML_TAG_RE.split(text)
    result = []
    for part in parts:
        if not part:
            continue
        if XML_TAG_RE.fullmatch(part):
            result.append(part)
        else:
            result.append(sanscript.transliterate(part, inputTranslit, 'devanagari'))
    return ''.join(result)


def transliterate_metaline_keys(line, inputTranslit):
    """Transliterate only the <k1>/<k2> values of ONE metaline, in place.

    Buys what the old parseheadline -> dict -> reserialise round trip lost: a
    metaline may repeat a tag (`<e>,ulapya/<e>2B` in MW), and a dict keeps only
    the last value, so every earlier duplicate vanished from the mirror (bughunt
    26-10-2026 finding 4). Everything outside the two text fields — tag order,
    duplicates, trailing spaces, unknown tags — is returned untouched.
    """
    parts = XML_TAG_RE.split(line)
    result = []
    current = None
    for part in parts:
        if not part:
            continue
        if XML_TAG_RE.fullmatch(part):
            current = part[1:-1]
            result.append(part)
        elif current in METALINE_TEXT_KEYS:
            result.append(sanscript.transliterate(part, inputTranslit, 'devanagari'))
        else:
            result.append(part)
    return ''.join(result)


def convert_metaline(dictcode):
    """Convert k1 and k2 from metaline to Devanagari."""
    scheme = 'slp1_accented' if dictcode in ACCENTED_DICTS else 'slp1'
    # Read data
    filein = os.path.join('..', 'v02', dictcode, dictcode + '.txt')
    fin = codecs.open(filein, 'r', 'utf-8')
    data = fin.read()
    fin.close()
    # Initialize result list
    result = []
    # Read into lines
    lines = data.split('\n')
    # For each line
    for lin in lines:
        # If metaline, convert its k1/k2 values; every other line is unchanged.
        if lin.startswith('<L>'):
            result.append(transliterate_metaline_keys(lin, scheme))
        else:
            result.append(lin)
    # Write the result to the output file (the same as input file.)
    fout = codecs.open(filein, 'w', 'utf-8')
    fout.write('\n'.join(result))
    fout.close()


def convert_to_devanagari(data, inputTranslit='slp1'):
    """Convert to Devanagari generically."""
    result = []
    # Read into lines
    lines = data.split('\n')
    # For each line
    for lin in lines:
        # If no manipulation required,
        if lin.startswith('<L>') or lin.startswith('[Page') or lin.startswith('<H>') or lin.startswith('<LEND>'):
            # Keep as it is.
            result.append(lin)
        # If manipulation is required,
        else:
            # Convert to Devanagari.
            result.append(transliterate_text_preserving_xml_tags(lin, inputTranslit))
    # Prepare result
    return '\n'.join(result)


def convert_partially_to_devanagari(startMark, endMark, inputTranslit, data):
    """Convert to Devanagari based on startMark and endMark."""
    # Prepare regex
    reg = re.escape(startMark) + '.*?' + re.escape(endMark)
    # Prepare split
    splt = re.split(r'(' + reg + ')', data)
    result = []
    for i in range(len(splt)):
        # If even, it is not to be converted
        if i % 2 == 0:
            result.append(splt[i])
        # If odd, it is to be converted to Devanagari.
        else:
            textToConvert = splt[i][len(startMark):-len(endMark)]
            result.append(startMark + transliterate_text_preserving_xml_tags(textToConvert, inputTranslit) + endMark)
    # Return the output
    return ''.join(result)


def run_code(dictcode):
    """Run different functions based on dictcode."""
    # Read file.
    filein = os.path.join('..', '..', 'csl-orig', 'v02', dictcode, dictcode + '.txt')
    fin = codecs.open(filein, 'r', 'utf-8')
    data = fin.read()
    fin.close()
    # Initialize output file
    fileout = os.path.join('..', 'v02', dictcode, dictcode + '.txt')
    fout = codecs.open(fileout, 'w', 'utf-8')
    # Pick SLP1 scheme: accented only for Vedic dictionaries (GRA, ACC).
    scheme = 'slp1_accented' if dictcode in ACCENTED_DICTS else 'slp1'
    # Depending on the dictcode; apply various startMark, endMark and functions
    if dictcode in ['vcp', 'skd', 'armh']:
        data = convert_to_devanagari(data, scheme)
    elif dictcode in ['mw', 'krm']:
        data = convert_partially_to_devanagari('<s>', '</s>', scheme, data)
    else:
        data = convert_partially_to_devanagari('{#', '#}', scheme, data)
    # Write to the output file.
    fout.write(data)
    fout.close()


if __name__ == "__main__":
    # Fetch dictcode from argument
    dictcode = sys.argv[1]
    # Run code
    run_code(dictcode)
    # Convert metalines key1 and key2 to Devanagari.
    if dictcode not in ['ae', 'bor', 'mwe', 'ieg']:
        convert_metaline(dictcode)
