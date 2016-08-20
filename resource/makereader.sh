#!/bin/bash


COM="cat ../src/actanno.py | sed '/\#BEGCUT/,/\#ENDCUT/d' > actreader.py"
echo $COM
eval $COM

COM="chmod +x actreader.py"
echo $COM
eval $COM
