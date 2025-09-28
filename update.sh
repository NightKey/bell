#!bin/bash

echo $'\033]30;Bell Updater\007'

cd "$(dirname "$0")"

git remote update
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse @{u})

if [ "$LOCAL" != "$REMOTE" ]
then
    git pull
    echo "Updates installed!"
    exit 1
fi

exit 0