#!/bin/sh
#/opt/homebrew/bin/python3.13 -m venv ../venv
source ../venv/bin/activate
pip install setuptools build tox pytest
export PATH="${PATH}:${HOME}/local/bin"
./autogen.sh
./configure --disable-java --disable-r --disable-csharp  \
            CXXFLAGS='-O2 -std=c++17 -stdlib=libc++ -mmacosx-version-min=10.9 -I/opt/homebrew/include/' \
            LDFLAGS='-stdlib=libc++ -mmacosx-version-min=10.9'

code . --locale=en


#export PATH="$PATH:/path/to/your/directory"
#cmake -DCMAKE_INSTALL_PREFIX=${HOME}/local/ ..
#cmake --build . -j14 
#cmake --install . 
