#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -c 'import sys; assert sys.version_info >= (3, 12), "Python 3.12+ gerekli"'
exec python3 server.py --open-browser
