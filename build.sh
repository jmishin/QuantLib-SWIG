#!/bin/sh
#/opt/homebrew/bin/python3.13 -m venv ../venv
source ../venv39/bin/activate
pip install setuptools build tox pytest
export PATH="${PATH}:${HOME}/local/bin"
./autogen.sh
./configure --disable-java --disable-r --disable-csharp  \
            CXXFLAGS='-O2 -std=c++17 -stdlib=libc++ -mmacosx-version-min=10.9 -I/opt/homebrew/include/' \
            LDFLAGS='-stdlib=libc++ -mmacosx-version-min=10.9'

cd Python

rm -rf dist
make -j14
source ../../venv/bin/activate
pip install --force-reinstall dist/quantlib_vega-*.whl
DYLD_LIBRARY_PATH=$HOME/src/QuantLib/build/debug/ql python -c "import QuantLib as ql; print('Успешно! Версия:', ql.__version__)"



