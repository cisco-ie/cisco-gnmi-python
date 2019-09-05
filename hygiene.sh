#!/usr/bin/env bash
# Script which autoformats (black) and lints (pylint) code
pipenv run black --safe --verbose --exclude proto src/cisco_gnmi
# Many disabled to accomodate black disagreements...
# Many failures due to protos being runtime-functional and difficult to lint.
pipenv run pylint --disable line-too-long --disable pointless-string-statement --disable no-member --disable wrong-import-position --disable bad-continuation src/cisco_gnmi/*.py
