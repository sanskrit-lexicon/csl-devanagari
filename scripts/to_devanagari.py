# coding=utf-8
import codecs
import sys
import os
import re
from indic_transliteration import sanscript

def convert_to_devanagari(data):
	result = ''
	lines = data.split('\n')
	for lin in lines:
		if lin.startswith('[Page') or lin.startswith('<H>') or lin.startswith('<L>') or lin.startswith('<LEND>'):
			result += lin + '\n'
		else:
			result += sanscript.transliterate(lin, 'slp1', 'devanagari') + '\n'	
	return result

def run_code(dictcode):
	filein = os.path.join('..', '..', 'csl-orig', 'v02', dictcode, dictcode + '.txt')
	fin = codecs.open(filein, 'r', 'utf-8')
	data = fin.read()
	fin.close()
	fileout = os.path.join('..', 'v02', dictcode, dictcode + '.txt')
	fout = codecs.open(fileout, 'w', 'utf-8')
	data = convert_to_devanagari(data)
	fout.write(data)
	fout.close()
	
if __name__ == "__main__":
	dictcode = sys.argv[1]
	run_code(dictcode)
	
