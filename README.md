## Install

```bash
export PIP_INDEX_URL=https://pypi.org/simple  # to make sure you're using proper repos
virtualenv venv --python=python3.8
. venv/bin/activate
pip install -r requirements.txt
```

## Run
Scripts to handle files on local computer:
* find duplicates,
* check backups.

```bash
. venv/bin/activate

YaDisk="${HOME}/Yandex.Disk.localized"

./run.py photo-analyze \
  --dir "${YaDisk}/Photo/phone/" \
  --dir "${YaDisk}/Фотокамера/" \
  --skip "${YaDisk}/Photo/phone/2017-11 Mi5/Pictures"

deactivate
```

## Links

* https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif.html
* https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif/subsectime.html
* https://photo.stackexchange.com/questions/69959/when-is-each-of-these-exif-date-time-variables-created-and-in-what-circumstan
* http://www.metadataworkinggroup.org/pdf/mwg_guidance.pdf#page=37
