#!/usr/bin/python

from flask import Flask, request, make_response, Response
from slackclient import SlackClient
import json
import sys
import os,subprocess,time
import re
import pickle
import utils
import functions
from slack import Slack
from auth import Auth
from slack_db import SlackDB
import requests
from slack_config import SlackConfig
from teletraan import Teletraan
from slack_jenkins import SlackJenkins
import logging

class Restart(object):


  def __init__(self,app,action,formJson,service,env):
     self.app=app

     logging.basicConfig(filename='restart.log',level=logging.INFO,format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S") #INFO,WARNING

     self.slackConfig=SlackConfig()
     self.SLACK_BOT_TOKEN = self.slackConfig.get("SLACK_BOT_TOKEN") 
     self.slack_client = SlackClient(self.SLACK_BOT_TOKEN)

     self.slack=Slack(self.app)
     self.auth=Auth(self.app)
     self.slackDB=SlackDB(self.app)

     self.formJson=formJson
     self.user=formJson["user"]["name"]
     self.channel=formJson["channel"]["name"]
     self.channelId=formJson["channel"]["id"]
     self.action=action
     self.service=service
     self.env=env

     self.headers = {
        'content-type': 'application/json',
     }


     if ( not action == "" ):
        function="self." + action.encode('utf-8') + "()"
        output=eval(function)


  def __slackPost(self,text,title="",type="default",update=False,ts=0):

     if ( type == "default" ):
         color="#7CD197"
     elif ( type == "alert" ):
         color="#F35A00"

     if ( text.find("*") == -1 ):
       if ( text.find("http") == -1 ):
          text = "*" + text + "*"
       else:
          text = "*" + text
          text=text.replace("http",'* http')

     attachments = [
        {
        "color": color,
        "attachment_type": "default",
        "mrkdwn_in": ["text", "title"],
        "title" : title,
        "text" : text
        }
     ]

     if ( update == True and not ts == 0 ):
        response = self.slack_client.api_call(
          "chat.update",
          ts=ts,
          channel=self.channelId,
          mrkdwn=True,
          attachments=attachments
        )

     else:
        response = self.slack_client.api_call(
          "chat.postMessage",
          channel=self.channelId,
          mrkdwn=True,
          attachments=attachments
        )

     return(response)

  def __ecsRestart(self,env,service):

      parameters={"Cluster_name": "RtbMicroservices" , "profile": env , "Service_name" : service }
      slackJenkins=SlackJenkins(self.channel,"Microservice_restart_service",parameters)
      slackJenkins.buildJob()
      jobStatus=slackJenkins.getJobStatus()

  def clearHistory(self):
      logging.info("Clearing menu history")

      if ( os.path.isfile("menu/restart_services_services.db" )):
           os.remove("menu/restart_services_services.db")

      if ( os.path.isfile("menu/restart_env_envs.db" )):
           os.remove("menu/restart_env_envs.db")

  def restart(self):
     logging.info("restart {} {}".format(self.service,self.env)) 
     self.__slackPost("@{} restarting {} , environment ,{}".format(self.user,self.service,self.env))
     servicesMap=utils.readJson("services_map.json")
     teletraanServices=""

     services=self.service.split(",")
     for service in services:
       for serviceMap in servicesMap["services"]:

          if ( service.lower() == serviceMap["name"] ):
             if ( self.env in serviceMap and len(serviceMap[self.env]) > 0 ):

               if ( serviceMap["type"] == "teletraan" ):
                 if ( self.env in serviceMap ):
                   for envs in serviceMap[self.env]:
                     if ( "envs" in envs ): 
                       for env in envs["envs"].split(","):
                          (output,status) = utils.runCmd("./teletraan.py restart \"{}\" {} {} {}".format(self.formJson,env,service.lower(),"restart"))
                 else:
                    (output,status) = utils.runCmd("./teletraan.py restart \"{}\" {} {} {}".format(self.formJson,self.env,service.lower(),"restart"))

             elif ( serviceMap["type"] == "ecs" ):
                   self.__ecsRestart(self.env,service) 

     self.clearHistory()
     self.__slackPost("@{} restart of {} , environment ,{} finished".format(self.user,self.service,self.env))


#---------------------------------------------------------------------------------------
def main():

   if ( len(sys.argv) < 3 ):
      print "Usage: <action> <payload> <services> <env>"
      sys.exit(0)
  
   app = Flask(__name__)

   action=sys.argv[1]
   services=sys.argv[3]
   env=sys.argv[4]
   formJson=utils.parseJson(sys.argv[2])

   restart=Restart(app,action,formJson,services,env)

if __name__ == "__main__":
   main()


