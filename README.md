```shell
virtualenv venv --python=python3.8
. venv/bin/activate
make vendor

./run.py --help

deactivate
```

## Links

* https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif.html
* https://www.awaresystems.be/imaging/tiff/tifftags/privateifd/exif/subsectime.html
* https://photo.stackexchange.com/questions/69959/when-is-each-of-these-exif-date-time-variables-created-and-in-what-circumstan
* http://www.metadataworkinggroup.org/pdf/mwg_guidance.pdf#page=37

## pyenv

* https://github.com/pyenv/pyenv#unixmacos
* https://github.com/pyenv/pyenv-virtualenv

```shell
git clone https://github.com/pyenv/pyenv.git ~/.pyenv
git clone https://github.com/pyenv/pyenv-virtualenv.git $(pyenv root)/plugins/pyenv-virtualenv

# add to ~/,zshrc
export PYENV_ROOT="${HOME}/.pyenv"
export PATH="${PYENV_ROOT}/bin:${PATH}"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv install --list | grep -E '^ +3\.\d{1,2}\.\d+$'
pyenv install 3.10.13

pyenv local 3.10.13
pyenv virtualenv 3.10.13 treashure-3.10.13
```
