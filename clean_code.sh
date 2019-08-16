#!/usr/bin/env bash
pipenv run black --safe --verbose --exclude proto gnmi
# Many disabled to accomodate black disagreements...
# Many failures due to protos being runtime-functional and difficult to lint.
pipenv run pylint --disable line-too-long --disable pointless-string-statement --disable no-member --disable wrong-import-position --disable wrong-import-position --disable bad-continuation gnmi/*.py
