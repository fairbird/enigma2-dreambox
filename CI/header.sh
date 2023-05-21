#!/bin/sh

echo ""
echo "Python header cleanup by Persian Prince"
# Script by Persian Prince for https://github.com/OpenVisionE2
# You're not allowed to remove my copyright or reuse this script without putting this header.
echo ""
echo "Changing py files, please wait ..." 
begin=$(date +"%s")

find . -type f -name "*.py" | xargs -L1 sed -i '/^#!\/usr\/bin\/env/d' # Avoid "#!/usr/bin/env python" lines and remove them all.
find . -type f -name "*.py" | xargs -L1 sed -i '/ coding:/d' # Avoid duplicate "# -*- coding: utf-8 -*-" lines and remove them all.
#find . -type f -name "*.py" | xargs -L1 sed -i '/print_function/d' # Avoid duplicate "from __future__ import print_function" lines and remove them all.
find . -type f -name "*.py" | xargs -L1 sed -i '/^#!\/usr\/bin\/python/d' # Avoid duplicate "#!/usr/bin/python" lines and remove them all.
find . -type f -name "*.py" | xargs -L1 sed -i '1i# -*- coding: utf-8 -*-' # Add "# -*- coding: utf-8 -*-" as the second line, always!

git add -u
git add *
git commit -m "Python header cleanup"

echo ""
finish=$(date +"%s")
timediff=$(($finish-$begin))
echo -e "Change time was $(($timediff / 60)) minutes and $(($timediff % 60)) seconds."
echo -e "Fast changing would be less than 1 minute."
echo ""
echo "Cleanup Done!"
echo ""
