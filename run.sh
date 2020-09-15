#!/usr/bin/env bash
set -xue -o posix -o pipefail

vDir='tmp'
# virtualenv "${vDir}"
. "./${vDir}/bin/activate"
pip install pillow
pip install soundcloud
pip install six
pip install eyeD3
# ${1}
./mobile.py --file
deactivate

YD='/Users/burmisha/Yandex.Disk.localized'
  # --dir "${YD}/Фотокамера/" \
./mobile.py parse \
  --dir "${YD}/Photo/phone/" \
  --exclude "${YD}/Photo/phone/2017-11 Mi5/Pictures"

# https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif.html
# https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif/subsectime.html
# https://photo.stackexchange.com/questions/69959/when-is-each-of-these-exif-date-time-variables-created-and-in-what-circumstan
# http://www.metadataworkinggroup.org/pdf/mwg_guidance.pdf#page=37
