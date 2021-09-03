# coding=utf-8
"""Convert Sanskrit text from Devangari to SLP1 transliteration.
    Author - Dr. Dhaval Patel
    email - drdhaval2785@gmail.com
    date - 03 September 2021
    Usage - python3 to_slp1.py dictcode
    e.g. - python3 to_slp1.py mw
"""
import codecs
import sys
import os
import re
from indic_transliteration import sanscript


def convert_metaline(dictcode):
    """Convert metaline k1 and k2 to SLP1."""
    # Read data
    filein = os.path.join('..', 'slp1', dictcode + '.txt')
    fin = codecs.open(filein, 'r', 'utf-8')
    data = fin.read()
    fin.close()
    result = []
    # Read into lines
    lines = data.split('\n')
    for lin in lines:
        # If metaline,
        if lin.startswith('<L>'):
            # Convert to slp1
            result.append(sanscript.transliterate(lin, 'devanagari', 'slp1'))
        else:
            # If not metaline, keep it as it is.
            result.append(lin)
    # Write to the output file (the same as input file)
    fout = codecs.open(filein, 'w', 'utf-8')
    fout.write('\n'.join(result))
    fout.close()


def convert_to_slp1(data):
    """Convert to SLP1 generically."""
    result = []
    # Read into lines
    lines = data.split('\n')
    for lin in lines:
        # If no change needed, keep it as it is.
        if lin.startswith('<L>') or lin.startswith('[Page') or lin.startswith('<H>') or lin.startswith('<LEND>'):
            result.append(lin)
        # If change required,
        else:
            # Convert to SLP1.
            result.append(sanscript.transliterate(lin, 'devanagari', 'slp1'))
    # Return the result
    return '\n'.join(result)


def convert_partially_to_slp1(startMark, endMark, outputTranslit, data):
    """Convert to SLP1 based on startMark, endMark."""
    # Preprare regex.
    reg = startMark + '.*?' + endMark
    # Split
    splt = re.split(r'(' + reg + ')', data)
    result = []
    for i in range(len(splt)):
        # If even,
        if i % 2 == 0:
            # Keep it as it is.
            result.append(splt[i])
        # If odd,
        else:
            # Transliterate to SLP1
            result.append(sanscript.transliterate(splt[i], 'devanagari', outputTranslit))
    # Return output
    return ''.join(result)


def run_code(dictcode):
    """Run appropriate code as per the dictcode."""
    # Read the data.
    filein = os.path.join('..', 'v02', dictcode, dictcode + '.txt')
    fin = codecs.open(filein, 'r', 'utf-8')
    data = fin.read()
    fin.close()
    # Initialize output file.
    fileout = os.path.join('..', 'slp1', dictcode + '.txt')
    fout = codecs.open(fileout, 'w', 'utf-8')
    # Apply appropriate function, startMark, endMark.
    if dictcode in ['vcp', 'skd', 'armh']:
        data = convert_to_slp1(data)
    elif dictcode in ['mw', 'krm']:
        data = convert_partially_to_slp1('<s>', '</s>', 'slp1', data)
    # elif dictcode in ['ap90', 'mwe', 'bor', 'ae', 'pwg', 'pw', 'ccs', 'mw72', 'bop', 'inm', 'vei', 'pui', 'bhs', 'acc', 'ieg', 'snp', 'pe', 'pgn', 'mci', 'ben', 'bur', 'gst', 'lan', 'md', 'sch', 'shs', 'stc', 'wil', 'yat', 'gra']:
    else:
        data = convert_partially_to_slp1('{#', '#}', 'slp1', data)
    # Write result to output file.
    fout.write(data)
    fout.close()


if __name__ == "__main__":
    # Fetch dictcode from argument.
    dictcode = sys.argv[1]
    # Apply appropriate code for transliteration.
    run_code(dictcode)
    # Convert metaline k1, k2 to SLP1.
    convert_metaline(dictcode)
