#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $DIR
FLASK_PORT=$(grep "FLASK_PORT=" $DIR/slack.cfg  | cut -f2 -d\=)

start()
{
  export FLASK_APP=slack_server.py
  export FLASK_DEBUG=1
  flask run --host=0.0.0.0 -p ${FLASK_PORT}
}

stop()
{
   curl http://localhost:${FLASK_PORT}/shutdown
   echo
}

restart()
{
    stop
    start
}

case "$1" in
    start|stop|restart)
      $1
      ;;

    *)
      start
      ;;
esac

