#!/bin/bash
echo "UPDATE CSL-ORIG REPOSITORY."
cd ../../csl-orig || exit 1
git pull --ff-only origin main || exit 1
cd ../csl-devanagari/scripts || exit 1
echo "UPDATING CSL-ORIG COMPLETED."
echo ""
mkdir -p ../slp1

dicts=(wil yat gst ben mw72 lan lrv ap90 cae md mw shs mwe bor ae bur stc pwg gra pw ccs sch bop armh vcp skd abch acph acsj inm vei pui bhs acc krm ieg snp pe pgn mci)
for dict in "${dicts[@]}";
do
	echo "STARTED CONVERTING $dict";
	bash redo.sh $dict;
	echo "";
done
