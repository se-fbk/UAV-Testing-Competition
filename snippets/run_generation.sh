#!/bin/sh

# initialize environment
# INIT_ENV_SCRIPT="/src/generator/initialize_env.sh"
# if [ ! -f $INIT_ENV_SCRIPT ] ; then
#    echo "File "$INIT_ENV_SCRIPT" not found"
#    exit 1
# fi

# echo "Init environment"
# sh $INIT_ENV_SCRIPT

# create local log file beacuse of permissions issue
mkdir /root/.ros
chmod 777 /root/.ros

# go to /src/generator
echo "Go to working dir"
WORKING_FOLDER="/src/generator/"
# if [ ! -d $WORKING_FOLDER ] ; then
#    echo "Folder "$WORKING_FOLDER" not found"
#    exit 1
# fi
cd $WORKING_FOLDER
pwd

# parameters are mission and budget
MISSION=$1
BUDGET=$2

echo "Run generation"
python3 cli.py generate $MISSION $BUDGET # &
# BACK_PID=$!

# while kill -0 $BACK_PID ; do
#    echo "Process is still active..."
#    sleep 10
# done

# $BACK_PID

# exit 0
