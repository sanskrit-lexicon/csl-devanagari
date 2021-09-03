# Workflow

1. This repository generates files in which Devanagari script is used instead of SLP1 (as in csl-orig)
2. The data from csl-orig repository is processed via script to_devanagari.py and stored in v02/dict/dict.txt file in the present repository.
3. To ensure that the change is reversible, a script to_slp1.py is also prepared.
4. After one pass from to_devanagari.py and to_slp1.py, the result is stored in slp1/dict.txt file.
5. slp1/dict.txt file is compared with csl-orig/v02/dict/dict.txt file.
6. slp1 folder is not tracked in this repository, as it is only holds intermediate files for comparision.
7. If there are any differences noted, they are shown in diff/dict.txt file in this repository.
8. Ideal situation should be that there is no difference between both files.


# How to regenerate for a specific dictionary?

`cd scripts; bash redo.sh dict` e.g. `cd scripts; bash redo.sh mw`


# How to regenerate for all dictionaries?

`cd scripts; bash redo_all.sh`

