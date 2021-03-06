echo "UPDATE CSL-ORIG REPOSITORY."
cd ../../csl-orig
git pull origin master
cd ../csl-devanagari/scripts
echo "UPDATING CSL-ORIG COMPLETED."
echo ""
mkdir -p ../slp1

dicts=(wil yat gst ben mw72 lan cae md mw shs ap90 mwe bor ae bur stc pwg gra pw ccs sch bop armh vcp skd inm vei pui bhs acc krm ieg snp pe pgn mci)
for dict in ${dicts[@]};
do
	echo "STARTED CONVERTING $dict";
	bash redo.sh $dict;
	echo "";
done
