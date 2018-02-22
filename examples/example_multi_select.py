#!/usr/bin/python

import sys,os
scriptDir=os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, scriptDir + "/../")

import utils
from slackclient import SlackClient
from slack_config import SlackConfig

if ( len(sys.argv) < 3 ):
   print("Usage: <payload>")
   sys.exit()

payload=utils.parseJson(sys.argv[1])
channelName=payload["channel"]["name"]
channelId=payload["channel"]["id"]

slackConfig=SlackConfig()
SLACK_BOT_TOKEN = slackConfig.get("SLACK_BOT_TOKEN")
slack_client = SlackClient(SLACK_BOT_TOKEN)

print("in example.py " + str(sys.argv[2]))

response = slack_client.api_call(
        "chat.postMessage",
        channel=channelId,
        mrkdwn=True,
        text="*hello from python example*\nSelected arguments:"+sys.argv[2]
)
