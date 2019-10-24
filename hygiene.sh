#!/usr/bin/env bash
# Script which autoformats (black) and lints (pylint) code
echo "Running black ..."
FORMAT_COMMAND="black --safe --verbose --exclude proto src/cisco_gnmi tests/"
if black &> /dev/null; then
    eval $FORMAT_COMMAND
elif pipenv run black &> /dev/null; then
    eval "pipenv run $FORMAT_COMMAND"
else
    echo "black formatter not found on system, proceeding to pylint..."
fi
echo "Running pylint ..."
# Many failures due to protos being runtime-functional and difficult to lint.
pipenv run pylint --disable no-member --disable wrong-import-position --disable bad-continuation src/cisco_gnmi/*.py
