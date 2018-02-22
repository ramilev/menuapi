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
import requests
import time
import os
import logging

class Teletraan(object):

   def __init__(self,app,action,formJson,stage,env,version,buildName=""):

     if ( app == None ):
        self.app = Flask(__name__)
     else:
        self.app=app

     logging.basicConfig(filename='teletraan.log',level=logging.INFO,format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S") #INFO,WARNING

     self.maxDisplayAgents=100
     self.slackConfig=SlackConfig()

     self.slack=Slack(self.app)
     self.auth=Auth(self.app)
     self.slackDB=SlackDB(self.app)

     self.formJson=formJson
     if ( not self.formJson == {} ) :
        self.user=formJson["user"]["name"]
        self.channel=formJson["channel"]["name"]
        self.channelId=formJson["channel"]["id"]
     

     self.action=action

     self.stage=stage
     self.env=env
     self.version=version
     self.buildName=buildName

     self.SLACK_BOT_TOKEN = self.slackConfig.get("SLACK_BOT_TOKEN")
     self.slack_client = SlackClient(self.SLACK_BOT_TOKEN)
     self.teletraanUrl=self.slackConfig.get("teletraan_url")

     self.headers = {
        'content-type': 'application/json',
     }


     if ( not action == "" ):
        function="self." + action.encode('utf-8') + "()"
        output=eval(function)
     

   def __loadVars(self):

      self.feature=self.slackDB.get("feature")
      self.plan=self.slackDB.get("plan")
      self.qa_approved = self.slackDB.get('qa_approved')
      self.release_manager_approved = self.slackDB.get('release_manager_approved')
      self.original_user = self.slackDB.get('original_user')
      self.finished = self.slackDB.get('finished')
      self.started = self.slackDB.get('started')
      self.email = self.slackDB.get('email')

      #admin
      self.admin_started = self.slackDB.get('admin_started')
      self.admin_finished = self.slackDB.get('admin_finished')
      self.bluetogreen = self.slackDB.get('bluetogreen')
      self.sanitypass = self.slackDB.get('sanitypass')

      #ecs
      self.ecs_started = self.slackDB.get('ecs_started')
      self.ecs_finished = self.slackDB.get('ecs_finished')
      self.ecs_sanitypass = self.slackDB.get('ecs_sanitypass')


   def __slackPostStatus(self,success,failed,total,acceptanceStatus,title="",ts=0):



     fields=[]
     fields.append ( { "title" : "Success" , "value": str(success) , "short": True } )
     fields.append ( { "title" : "Failed" , "value": str(failed), "short": True } )
     fields.append ( { "title" : "Status" , "value": acceptanceStatus , "short": True } )
     fields.append ( { "title" : "Total" , "value": str(total), "short": True } )


     color="#7CD197"
     attachments = [
        {
           "color": color,
           "attachment_type": "default",
           "text" : "",
           "title": title,
           "unfurl_media": False,
           "short": True,
           "mrkdwn_in": ["text", "title"],
           "fields" : fields
        }
     ]


     if ( ts > 0 ):
       chat="chat.update"
     else:
       chat="chat.postMessage"

     response = self.slack_client.api_call(
        chat,
        channel=self.channelId,
        mrkdwn=True,
        attachments=attachments,
        ts=ts
     )

     #logging.info("_slackPostStatus: {}".format(response))
     return(response)

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


   def restart(self):

     self.app.logger.debug("restarting {},{}".format(self.stage,self.env))
     self.__slackPost("restarting teletraan {},{}".format(self.stage,self.env))

     url="{}/v1/envs/{}/{}/deploys/current/actions?actionType=RESTART".format(self.teletraanUrl,self.env,self.stage)
     result = requests.post(url, headers=self.headers)
     resultJson = result.json()
     if ( "code" in resultJson and not resultJson["code"] == 200 ):
       self.__slackPost("<@{}> Teletraan restart failed: `{}` ".format(self.user,resultJson["message"]),type="alert")
       return(1)

     self.deployId=resultJson["id"]
     self.getDeployStatus()


   def getStages(self):

     stages=[]
     url=self.teletraanUrl + "/v1/envs?envName=" + self.env
     result = requests.get(url, headers=self.headers)
     resultJson = result.json()
   
     self.app.logger.debug(resultJson)

     for env in resultJson:
       if ( "stageName" in env ):
         self.app.logger.debug(env["stageName"])
         stages.append( { "value" : env["stageName"] , "text" : env["stageName"] , "label": env["stageName"] } )

     return(stages)


   def getBuilds(self):

     url=self.teletraanUrl + "/v1/builds/names"
     result = requests.get(url, headers=self.headers)
     resultJson = result.json()

     builds=[]
     for build in resultJson:
       self.app.logger.debug(build)
       builds.append( { "value" : build , "text" : build , "label": build } )

     self.app.logger.debug(builds)
     return(builds)


   def getBuildVersions(self):

     url=self.teletraanUrl + "/v1/builds?name=" + self.env
     result = requests.get(url, headers=self.headers)
     resultJson = result.json()

     versions=[]
     for build in resultJson:

       if ( utils.daysCompare(build["commitDate"]) < 30 ):
         print build["branch"], utils.convertToDate(build["commitDate"]),utils.convertDisplayTime(build["commitDate"])

         self.app.logger.debug(build["branch"], utils.convertToDate(build["commitDate"]))

         value=build["branch"] + "-" + utils.convertDisplayTime(build["commitDate"])
         versions.append( { "value" : value , "text" : value , "label": value } )

     return(versions)


   def __getBuildId(self):

     if ( self.buildName == "" ):
        url=self.teletraanUrl + "/v1/builds?name=" + self.env
     else:
        url=self.teletraanUrl + "/v1/builds?name=" + self.buildName

     result = requests.get(url, headers=self.headers)
     resultJson = result.json()

     foundBuildId=""
     latestTime=0

     for build in resultJson:

       menuValue=""
       branch=""
       branchTime=0
       
       if ( "branch" in build ):
         branch=os.path.basename(build["branch"])
         branchTime=utils.convertTime(build["commitDate"])
         menuValue=build["branch"] + "-" + utils.convertDisplayTime(build["commitDate"])
       
       #find build id from menu
       if ( menuValue == self.version ):
          return(build["id"])
      
       #get last build id based on branch
       if ( branch == self.version and branchTime >= latestTime ):
          latestTime=branchTime
          foundBuildId=build["id"]
     
     return(foundBuildId)

   def deploy(self):
    
     self.buildId=self.__getBuildId()

     if ( self.buildId == "" ):
       self.__slackPost("<@{}> Teletraan deployment didnt find build id for version `{}` {}".format(self.user,self.version,self.env),type="alert")
       return

     payload={'buildId': self.buildId}
     url=self.teletraanUrl + "/v1/envs/{}/{}/deploys?buildId={}".format(self.env,self.stage,self.buildId)

     result = requests.post(url, data=json.dumps(payload),headers=self.headers)
     resultJson = result.json()
     self.app.logger.debug(resultJson)
     
     if ( "code" in resultJson and not resultJson["code"] == 200 ):
       self.__slackPost("<@{}> Teletraan deployment failed: `{}` ".format(self.user,resultJson["message"]),type="alert")
       return(1)


     self.deployId=resultJson["id"]
     self.__slackPost("<@{}> deployment {} status `{}` ".format(self.user,self.version.replace("-"," "),
        resultJson["acceptanceStatus"]),title=self.env + " " + self.stage + " deployment")
     deployStatus=self.getDeployStatus()

     return(deployStatus)


   def __getDeployState(self):

     url=self.teletraanUrl + "/v1/deploys/{}".format(self.deployId)
     result = requests.get(url,headers=self.headers)
     resultJson = result.json()
     #logging.info(resultJson)
     return(resultJson["state"],resultJson["successTotal"],resultJson["failTotal"],resultJson["acceptanceStatus"])
 

   def getDeployStatus(self):

     deployState=""
     count=0
     totalDeloyed=0
     agentsCount=1
     successTotal=0
     failTotal=0
     ts=0
     deployStatus=0
     agentsTs={}
     acceptanceStatus=""

     
     while ( agentsCount > 0 and not agentsCount == ( successTotal + failTotal ) ):

   
       url=self.teletraanUrl + "/v1/envs/{}/{}/deploys/current/progress".format(self.env,self.stage)
       result = requests.put(url, headers=self.headers)
       resultJson = result.json()
       #logging.info(resultJson)

       #print self.env,self.stage,self.version.replace("-"," ")

       deployState,successTotal,failTotal,acceptanceStatus=self.__getDeployState()

       if ( "agents" in resultJson ):

         agentsCount=len(resultJson["agents"])

         for agent in resultJson["agents"]:

           if [ agent["status"] == "SUCCEEDED" ]:
             msgType="default" 
           else:
             msgType="alert" 


           if ( agentsCount < self.maxDisplayAgents ):

             if ( self.action == "restart" ):
               title=self.env + " " + self.stage + " agent restart"
             else:
               title=self.env + " " + self.stage + " agent deployment version {}".format(self.version.replace("-"," "))
 
             if ( ts == 0 ):
               response=self.__slackPostStatus(successTotal,failTotal,agentsCount,acceptanceStatus,title)
             else:
               response=self.__slackPostStatus(successTotal,failTotal,agentsCount,acceptanceStatus,title,ts)

             logging.info("{} {} {} {}".format(ts,successTotal,failTotal,agentsCount))

             if ( "ts" in response and "hostId" in agent ):

               ts=response["ts"]
               logging.info("getting ts="+response["ts"]+",hostid=" + str(agent["hostId"]))
               
               if ( not agent["hostId"] in agentsTs ):
                 agentsTs[agent["hostId"]]=ts



       logging.info("**** deployState {},agentsCount {},successTotal {},failTotal {}".format(deployState,agentsCount,successTotal,failTotal))
 
       time.sleep(5)

     if ( failTotal > 0 ):
        msgType="alert"
        deployStatus=1
        deployIcon=":x:"
     else:
        msgType="default"
        deployIcon=":white_check_mark:"


     if ( self.action == "restart" ):
        action="Restart"
        
     else:
        action="Deployment"

     self.__slackPost("<@{}> Success: `{}` Failed: `{}` ".format(self.user,successTotal,failTotal),title="{} {} {} {} finished {}".format(deployIcon,action,self.env,self.stage,deployState),type=msgType)


     return(deployStatus)

def main():

   if ( len(sys.argv) < 3 ):
      print "Usage: <action> <payload> <stage name> <env name> <version>"
      print "action: getBuilds"
      sys.exit(0)

   app = Flask(__name__)

   formJson=utils.parseJson(sys.argv[2])
   if ( len(sys.argv) == 4 ):
     stage=sys.argv[3]
     env=""
     version=""

   elif ( len(sys.argv) == 6 ):
     stage=sys.argv[3]
     env=sys.argv[4]
     version=sys.argv[5]

   elif ( len(sys.argv) == 5 ):
     stage=sys.argv[3]
     env=sys.argv[4]
     version=""

   else:
     stage=""
     env=""
     version=""


   teletraan=Teletraan(app,sys.argv[1],formJson,stage,env,version)


if __name__ == "__main__":
   main()


