echo "Convert to Devanagari."
python3 to_devanagari.py $1
echo "Convert back to SLP1."
python3 to_slp1.py $1
echo "Store differences in ../diff/$1.txt."
diff ../slp1/$1/$1.txt ../../csl-orig/v02/$1/$1.txt > ../diff/$1.txt
echo "Complete."
