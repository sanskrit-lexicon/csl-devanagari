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
from parseheadline import parseheadline


def convert_metaline(dictcode):
    """Convert k1 and k2 from metaline to Devanagari."""
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
        # If metaline,
        if lin.startswith('<L>'):
            # parse the metaline
            meta = parseheadline(lin)
            devameta = []
            for i in meta:
                # meta tag
                devameta.append('<' + i + '>')
                # Convert content of k1 and k2 into Devangari.
                if i in ['k1', 'k2']:
                    devameta.append(sanscript.transliterate(meta[i], 'slp1_accented', 'devanagari'))
                # Keep rest of content as they are.
                else:
                    devameta.append(meta[i])
            # Prepare result line
            result.append(''.join(devameta))
        else:
            # If not metaline, no change is affected.
            result.append(lin)
    # Write the result to the output file (the same as input file.)
    fout = codecs.open(filein, 'w', 'utf-8')
    fout.write('\n'.join(result))
    fout.close()


def convert_to_devanagari(data):
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
            result.append(sanscript.transliterate(lin, 'slp1_accented', 'devanagari'))
    # Prepare result
    return '\n'.join(result)


def convert_partially_to_devanagari(startMark, endMark, inputTranslit, data):
    """Convert to Devanagari based on startMark and endMark."""
    # Prepare regex
    reg = startMark + '.*?' + endMark
    # Prepare split
    splt = re.split(r'(' + reg + ')', data)
    result = []
    for i in range(len(splt)):
        # If even, it is not to be converted
        if i % 2 == 0:
            result.append(splt[i])
        # If odd, it is to be converted to Devanagari.
        else:
            textToConvert = re.sub('^' + startMark, '', splt[i])
            textToConvert = re.sub(endMark + '$', '', textToConvert)
            result.append(startMark + sanscript.transliterate(textToConvert, inputTranslit, 'devanagari') + endMark)
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
    # Depending on the dictcode; apply various startMark, endMark and functions
    if dictcode in ['vcp', 'skd', 'armh']:
        data = convert_to_devanagari(data)
    elif dictcode in ['mw', 'krm']:
        data = convert_partially_to_devanagari('<s>', '</s>', 'slp1_accented', data)
    else:
        data = convert_partially_to_devanagari('{#', '#}', 'slp1_accented', data)
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
