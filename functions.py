#!/usr/bin/python 

import pprint
import ConfigParser
import traceback
import sys,os,subprocess,time
import json
import re
import utils
import requests
from teletraan import Teletraan

maxGitValues=60

def getConfluencePlans(value=""):

  headers = {
    'content-type': 'application/json',
  }
  url="http://bot.infra:123456@confluence.matomy.local/rest/api/content/search?limit=90&cql=space=RTB%20and%20title%20~%20'Deployment%20Plan'%20and%20lastModified>now('-12w')"
  result = requests.get(url, headers=headers)
  resultJson = result.json()

  plans=[]
  for plan in resultJson["results"]:
    planTitle=plan["title"].replace("Deployment Plan - ","")
    if ( not planTitle.find("") ):
      if ( value == "" ):
        plans.append( { "value" : planTitle , "text" : planTitle } )
      else:
        plans.append( { "value" : value , "text" : planTitle } )

  return(plans)

  

def getRTBGitBranches():
  #(output,status)=runCmd("git ls-remote ssh://devops@10.0.3.234:7999/rtb/rtb")
  (output,status)=utils.runCmd("cd git/rtb; git for-each-ref --sort=-committerdate | head -n" + str(maxGitValues))

  lines=re.split("\n",output)
  branchesBuffer=re.split(" ",output)
  branches=[]
  sortBranches=[]

  for line in lines:
    lineBuffer=re.split(" ",line)
    if ( len(lineBuffer) > 1 ):
      pos=lineBuffer[1].rfind("/")+1
      branch=lineBuffer[1]

      if ( not branch[pos::] in sortBranches ):
        sortBranches.append(branch[pos::])
        branches.append( { "value" : branch[pos::] , "text" : branch[pos::] , "label" : branch[pos::] } )

  return(branches)

def getExampleFunction():
   result=[]
   result.append ( { "value": "selection1", "text": "selction1"} )
   result.append ( { "value": "selection2", "text": "selction2"} )
   result.append ( { "value": "selection3", "text": "selction3"} )
   result.append ( { "value": "selection4", "text": "selction4"} )
   return(result)

def runFunction(runFunction):
  if ( "(" in runFunction  ):
    function=runFunction.encode('utf-8')
  else:
    function=runFunction.encode('utf-8') + "()"

  output=eval(function)
  return(output)


def getTeletraanGetStages(env):
    teletraan=Teletraan(None,"",{},"",env,"")
    teletraanOut=teletraan.getStages()
    return(teletraanOut)

def getTeletraangetBuildVersions(stage,env):
    teletraan=Teletraan(None,"",{},stage,env,"")
    teletraanOut=teletraan.getBuildVersions()
    return(teletraanOut)
 

def getTeletraanGetBuilds():
    teletraan=Teletraan(None,"",{},"","","")
    teletraanOut=teletraan.getBuilds()
    return(teletraanOut)


