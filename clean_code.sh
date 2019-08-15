#!/usr/bin/env bash
pipenv run black --safe --verbose --exclude proto gnmi
pipenv run pylint gnmi/*.py
