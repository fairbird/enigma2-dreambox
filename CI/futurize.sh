#!/bin/sh

echo ""
echo "2to3 safe cleanup by Persian Prince"
# Script by Persian Prince for https://github.com/OpenVisionE2
# You're not allowed to remove my copyright or reuse this script without putting this header.
echo ""
echo "Changing py files, please wait ..." 
begin=$(date +"%s")

# More information: https://docs.python.org/3/library/2to3.html

echo ""
echo "2to3 safe cleanup"
find . -name "*.py" -type f -exec 2to3 -f raise -f except -f has_key -f idioms -f paren -f ne -f isinstance -f exec -f apply -f execfile -f xreadlines -f numliterals -w -n {} \;
find . -name "*.bak" -type f -exec rm -f {} \;
git add -u
git add *
git commit -m "2to3 safe cleanup"

echo ""
finish=$(date +"%s")
timediff=$(($finish-$begin))
echo -e "Change time was $(($timediff / 60)) minutes and $(($timediff % 60)) seconds."
echo -e "Fast changing would be less than 5 minutes."
echo ""
echo "2to3 Done!"
echo ""
