dicts=(wil yat gst ben mw72 lan lrv ap90 cae md mw shs mwe bor ae bur stc pwg gra pw ccs sch bop armh vcp skd abch acph acsj inm vei pui bhs acc krm ieg snp pe pgn mci)
echo "STARTED TAKING CORRECTIONS FROM CSL-DEVANAGARI TO CSL-ORIG";
for dict in ${dicts[@]};
do
	echo $dict
	python3 to_slp1.py $dict
	cp ../slp1/$dict.txt ../../csl-orig/v02/$dict/$dict.txt
	echo "";
done
