#!/usr/bin/python

import jenkins
import sys
import time
import json
import urllib
from slackclient import SlackClient
from slack_config import SlackConfig
from slack_db import SlackDB
from flask import Flask, request, make_response, Response
import requests
import logging
import gc

class SlackJenkins(object):

   def __init__(self,channel,jobName,parameters):

      self.slackConfig=SlackConfig()

      logging.basicConfig(filename='slack_jenkins.log',level=logging.INFO,format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s', datefmt="%Y-%m-%d %H:%M:%S") #INFO,WARNING

      self.app = Flask(__name__)
      self.slackDB=SlackDB(self.app)

      self.jobName=jobName
      self.parameters=parameters
      self.SLACK_BOT_TOKEN = self.slackConfig.get("SLACK_BOT_TOKEN")
      self.jenkinsUrl = self.slackConfig.get("jenkins_url")
      self.jenkinsUsername = self.slackConfig.get("jenkins_username")
      self.jenkinsPassword = self.slackConfig.get("jenkins_password")
      self.jenkinsWaitTries = self.slackConfig.get("jenkins_waitTries")

      self.server=jenkins.Jenkins(self.jenkinsUrl, username=self.jenkinsUsername , password=self.jenkinsPassword)

      self.slack_client = SlackClient(self.SLACK_BOT_TOKEN)
      self.channel=channel

      self.__renderParameter()

      self.parentUpstreamBuild = 0 
      #last_build_number = self.server.get_job_info(jobName)['lastBuild']['number']
      #print self.server.get_build_info(jobName,61,1)["result"]
      #print self.server.get_build_info(jobName,61,1)["actions"][1]['causes'][0]['upstreamBuild']
      #sys.exit()

   def __renderParameter(self):

        buildParameters=[]
        for key,value in self.parameters.items():
          buildParameters.append({ "name": key , "value": value})

        self.parameters=buildParameters

   def __slackPost(self,text,type="default"):

     if ( type == "default" ):
         color="#7CD197"
     elif ( type == "alert" ):
         color="#F35A00"

     attachments = [
        {
        "color": color,
        "attachment_type": "default",
        "mrkdwn_in": ["text", "title"],
        "text" : text
        }
     ]

     response = self.slack_client.api_call(
        "chat.postMessage",
        channel=self.channel,
        mrkdwn=True,
        attachments=attachments
     )

   def __getupstreamBuild(self,jobName):

      buildNumber = self.server.get_job_info(jobName)['lastBuild']['number']
      buildInfo=self.server.get_build_info(jobName,buildNumber,1)

      if ( "actions" in buildInfo ):

        for buildAction in buildInfo["actions"]:
           if ( "causes" in buildAction ):
             for buildCauses in buildAction["causes"]:
                if ( "upstreamBuild" in buildCauses ):
                  logging.info("__getupstreamBuild={}".format(buildCauses["upstreamBuild"]))
                  return(buildCauses["upstreamBuild"])
 
      return(0)


   def __waitForTriggeredBuild(self,jobName):

      tries=0
      while True:

        triggeredBuildNumber = self.server.get_job_info(jobName)['lastBuild']['number']

        if ( self.parentUpstreamBuild > 0 and triggeredBuildNumber > 0 ):

          upstreamBuild=self.__getupstreamBuild(jobName)

          logging.info("upstreamBuild={}".format(upstreamBuild))
          if ( upstreamBuild == self.parentUpstreamBuild ):
            logging.info("triggeredBuildNumber={}".format(triggeredBuildNumber))
            return(triggeredBuildNumber)
        time.sleep(2)
        tries+=1
        if ( tries > 20 ):
           return(0)
          

   def __getJobOutput(self,jobName,triggeredBuildNumber=0):
 
      self.__slackPost( "Waiting for jenkins job `" + jobName + "`...." ,"default")
      logging.info("__getJobOutput:{} {}".format(jobName,triggeredBuildNumber))
      if ( not triggeredBuildNumber > 0 ):
         triggeredBuildNumber=self.__getBuildNumber(jobName)

      #wait for job
      #self.__slackPost( "Waiting for jenkins job `" + jobName + "`...." ,"default")
      self.__getBuildHistory(triggeredBuildNumber,jobName)
      time.sleep(2)

      #reconnect to jenkins
      self.server=None
      gc.collect()
      self.server=jenkins.Jenkins(self.jenkinsUrl, username=self.jenkinsUsername , password=self.jenkinsPassword)
      jobInfo=self.server.get_job_info(jobName)

      logging.info("jobname: {} getting build info {}".format(jobName,triggeredBuildNumber))

      tries=0
      while True:
         lastBuildNumber = self.server.get_job_info(jobName)['lastBuild']['number']
         logging.info("jobname: {} , tries: {} , last build: {} nextBuildNumber: {}".format(jobName,tries,lastBuildNumber,triggeredBuildNumber))

         if ( lastBuildNumber < triggeredBuildNumber ):
           tries+=1
           time.sleep(2)
         else:
           break

         if ( tries >= self.jenkinsWaitTries ):
            self.__slackPost( "Error: could not find jenkins job" ,"alert")
            return("")

      tries=0
      while self.server.get_build_info(jobName,triggeredBuildNumber,1)["building"] == True:
          tries+=1
          time.sleep(2)
          if ( tries >= self.jenkinsWaitTries ):
            self.__slackPost( "Error: timeout waiting for jenkins job" ,"alert")
            return("")
       
          if ( tries > 1 and tries % 30 == 0 ):
            self.__slackPost( "Still waiting for jenkins job to finish ...")
          
 
      self.parentUpstreamBuild=triggeredBuildNumber
      time.sleep(2)
      logging.info("jobname: {} , job output finished {}".format(jobName,triggeredBuildNumber))
      return(self.server.get_build_console_output(jobName,triggeredBuildNumber))


   def getJobStatus(self,buildNumber):

     self.output=self.__getJobOutput(self.jobName,buildNumber)
     triggeredJob=""
     jobName=self.jobName
     jobStatus=0

     while True:

       if ( "Finished: SUCCESS" in self.output ):
          self.__slackPost( "@channel *build " + jobName + " finished: `SUCCESS`*" ,"default")
          jobStatus=0
     
       if ( "Finished: FAILURE" in self.output ):
          self.__slackPost( "@channel *build " + jobName + " finished: `FAILURE`*" ,"alert")
          jobStatus=1

       if ( "Triggering a new build of" in self.output ):
          pos1=self.output.index("Triggering a new build of")
          triggeredJob=self.output[pos1+len("Triggering a new build of")+1:]
          pos2=triggeredJob.index("\n")
          triggeredJob=triggeredJob[:pos2]
          jobName=triggeredJob
          
          self.__slackPost( "Build *" + jobName + "* triggering a new build of *" + triggeredJob + "*" ,"default")
          triggeredBuildNumber=self.__waitForTriggeredBuild(jobName)
          self.output=self.__getJobOutput(triggeredJob,triggeredBuildNumber)

       else: 
          triggeredJob=""

       if ( triggeredJob == "" ):
          break

     return(jobStatus)


   def __getBuildHistory(self,nextBuildNumber,jobName):

      if ( nextBuildNumber > 1 ):
         buildInfo=self.server.get_build_info(jobName,nextBuildNumber-1,1)
         duration=float(buildInfo["duration"])/60000

         if ( buildInfo["result"] == "SUCCESS" ):
            if ( float(duration) < 1 ) :
               self.__slackPost("Last task duration was {} seconds".format( int(60 * duration) ),"default")
            else :
               minutes=int(duration)
               seconds=duration-minutes
               seconds=int(seconds*60)
               self.__slackPost("Last task duration was {} minutes {} seconds".format( minutes,seconds ),"default")


   def __getBuildNumber(self,jobName):
      return ( self.server.get_job_info(jobName)['nextBuildNumber'] )


   def displayJobOutput(self):
     self.output=self.__getJobOutput(self.jobName)
     print self.output

     return
     startDisplay=False
     for line in self.output.split("\n"):

        if ( startDisplay == True and not line[0:1] == "+" ):
           print "`" + line + "`"

        if ( line.find("[workspace]") > -1 ):
           startDisplay=True

   def buildJob(self):

      self.nextBuildNumber = self.server.get_job_info(self.jobName)['nextBuildNumber']

      url="{}/job/{}/build/api/json".format(self.jenkinsUrl,self.jobName)

      data = {"json": json.dumps({"parameter": self.parameters})}
      result = requests.post(url, auth=(self.jenkinsUsername,self.jenkinsPassword),data = data)

      if ( not result.status_code == 201 and not result.status_code == 200 ):
        self.__slackPost( "Failed to trigger Build *{}* error {}".format(self.jobName,result.status_code)  ,"alert")
        return(1)

      self.parentUpstreamBuild = self.nextBuildNumber
      return(self.nextBuildNumber)
      #old api
      #self.build=self.server.build_job(self.jobName,self.parameters)


def main():

    if ( len(sys.argv) < 3 ):
        print "Usage: <channel name> <job name> [json parameters] "
        sys.exit(1)

    if ( len(sys.argv) == 4 ):
      parameters=sys.argv[3]

      try:
        parameters=parameters.replace("'", "\"")
        parameters=json.loads(parameters)
        urllib.urlencode(parameters)
        
      except ValueError as e:
        print "Failed to parse parameters"
        sys.exit()

    else:
      parameters={}

    channel=sys.argv[1]
    jobName=sys.argv[2]


    slackJenkins=SlackJenkins(channel,jobName,parameters)
    buildNumber=slackJenkins.buildJob()
    slackJenkins.getJobStatus(buildNumber)

    #slackJenkins.displayJobOutput()


if __name__ == '__main__':
    #sys.exit(0)
    main()

