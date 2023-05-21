#!/bin/sh

echo ""
echo "Skin variable cleanup by Persian Prince"
# Script by Persian Prince for https://github.com/OpenVisionE2
# You're not allowed to remove my copyright or reuse this script without putting this header.
echo ""
echo "Changing xml files, please wait ..." 
begin=$(date +"%s")

find . -type f -name "*.xml" -exec sed -i "s|alphatest=|alphaTest=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|halign=|horizontalAlignment=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|hAlign=|horizontalAlignment=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|OverScan=|overScan=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarBackgroundPicture=|scrollbarBackgroundPixmap=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarbackgroundPixmap=|scrollbarBackgroundPixmap=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarSliderBorderColor=|scrollbarBorderColor=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarSliderBorderWidth=|scrollbarBorderWidth=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarSliderForegroundColor=|scrollbarForegroundColor=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarSliderPicture=|scrollbarForegroundPixmap=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|scrollbarSliderPixmap=|scrollbarForegroundPixmap=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|secondFont=|valueFont=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|secondfont=|valueFont=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|seek_pointer=|seekPointer=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|selectionDisabled=|selection=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|sliderPixmap=|scrollbarForegroundPixmap=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|valign=|verticalAlignment=|g" {} \;
find . -type f -name "*.xml" -exec sed -i "s|vAlign=|verticalAlignment=|g" {} \;

git add -u
git add *
git commit -m "XML variable cleanup"

echo ""
finish=$(date +"%s")
timediff=$(($finish-$begin))
echo -e "Change time was $(($timediff / 60)) minutes and $(($timediff % 60)) seconds."
echo -e "Fast changing would be less than 1 minute."
echo ""
echo "Cleanup Done!"
echo ""
