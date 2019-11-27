#!/bin/sh

exec python /app/manage.py migrate --noinput
