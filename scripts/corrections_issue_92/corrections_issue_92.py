# coding=utf-8
"""Transfer missing data to respective dictionaries.
    Author - Dr. Dhaval Patel
    email - drdhaval2785@gmail.com
    date - 06 September 2021
    Usage - python3 corrections_issue_92.py
"""
import codecs
import os
import re
from indic_transliteration import sanscript

def update_missing():
	corfin = codecs.open('Filling.the.missed.places.txt', 'r', 'utf-8')
	correctionData = corfin.read()
	corfin.close()
	correctionData = correctionData.replace('\r\n', '\n')
	dictwiseData = correctionData.split('------------------------\n')[:-1]
	for dictd in dictwiseData:
		for lin in dictd.split('\n')[:-1]:
			m = re.search('^([a-z0-9]*).txt$', lin)
			n = re.search('^\tLine ([0-9]+)\:\t(.*)$', lin)
			o = re.search('^\t\t([^%].*)$', lin)
			if m:
				dictcode = m.group(1)
				fin = codecs.open('../../v02/' + dictcode + '/' + dictcode + '.txt', 'r', 'utf-8')
				data = fin.read().split('\n')
				fin.close()
			elif n:
				linenum = int(n.group(1)) - 1
				old = n.group(2)
				new = ''
			elif o:
				new = o.group(1)
				print(linenum)
				print(data[linenum])
				print(new)
				data[linenum] = new
		fout = codecs.open('../../v02/' + dictcode + '/' + dictcode + '.txt', 'w', 'utf-8')
		result = '\n'.join(data)
		fout.write(result)
		fout.close()

if __name__ == "__main__":
	update_missing()

	
