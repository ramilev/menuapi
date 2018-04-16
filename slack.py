#!/usr/bin/python

import pprint
import ConfigParser
import traceback
import sys,os,subprocess,time
import json
import re
from flask import Flask, request, make_response, Response
import pickle
import utils
from auth import Auth
from slack_db import SlackDB
from slackclient import SlackClient
import functions
from slack_config import SlackConfig

class Slack(object):

  def __init__(self,app):
    self.app=app
    self.headers = {
        'content-type': 'application/json',
    }

    slackConfig=SlackConfig()
    self.SLACK_BOT_TOKEN = slackConfig.get("SLACK_BOT_TOKEN")
    self.slack_client = SlackClient(self.SLACK_BOT_TOKEN)

  def validateCommand(self,value,menu,validateType):
    self.app.logger.debug("Validate command " + value)

    validate=False
    if ( validateType == "" ):
      for option in menu[0]["actions"][0]["options"]:
         if ( "value" in option and value == option["value"]):
            validate=True
            print("validate found",option["value"])
    elif ( validateType == "dialog" ):
      if ( "value" in menu and menu["value"] == value ):
            validate=True
            print("validate found",menu["value"])
    else:
      for button in menu[0]["actions"]:
            print(button)
            if ( "name" in button and value == button["name"] ):
                validate=True
                print("validate found",button["name"])
            elif ( "value" in button and value == button["value"] ):
                validate=True
                print("validate found",button["value"])

    return(validate)



  #parse string with [xxx] and replace it with the menu value choosen or value from db
  def parseMenuValue(self,value,formJson,slackUserName="",shared=False):
    self.app.logger.debug("Parse command " + value + "," + slackUserName)

    if ( shared == True ):
      slackUserName=""
 
    searchBuffer=re.search('(\[.*\])',value.replace(" ",""))
    if ( searchBuffer ):
      searchBuffer=searchBuffer.groups()
    else:
      return(value)

    splitBuffer=re.split("[\[|\]]",searchBuffer[0])
    slackDB=SlackDB(self.app)
    value=value.replace(":","/")

    for splitItem in splitBuffer:

       self.app.logger.debug(splitItem)
       if ( not splitItem == "" ):

         if ( splitItem == "PAYLOAD" ):
           resultString=formJson

         elif ( splitItem == "USER" ):
           self.app.logger.debug(formJson)
           self.app.logger.debug(formJson["user"]["name"])
           if ( "user" in formJson ):
             resultString=formJson["user"]["name"]

         else:
           splitItem=splitItem.replace(":","/")

           if ( "/" in splitItem):
             menuName,selectName=splitItem.split("/")
           else:
             menuName=splitItem
             selectName=""

           data=self.loadMenuStatus(menuName,selectName,slackUserName,shared)
           resultString=""
           for dataItem in data:
            if ( not resultString == "" ):
              resultString+=","
            resultString+=dataItem

           if ( resultString == "" ):
             resultString=slackDB.get(splitItem)

         value=value.replace("[" + str(splitItem) + "]" , str(resultString))
         self.app.logger.debug("Parse value=" +value)

    return(value)

  def parseDialogValue(self,value,formJson):
    self.app.logger.debug("Parse command " + value)

    searchBuffer=re.search('(\[.*\])',value.replace(" ",""))
    if ( searchBuffer ):
      searchBuffer=searchBuffer.groups()
    else:
      return(value)

    splitBuffer=re.split("[\[|\]]",searchBuffer[0])

    resultString=""
    for splitItem in splitBuffer:

       self.app.logger.debug(splitItem)
       if ( not splitItem == "" ):

         if ( splitItem == "PAYLOAD" ):
           dialogValue=formJson

         elif ( splitItem == "USER" ):
           if ( "user" in formJson ):
             dialogValue=formJson["user"]["name"]

         elif ( not splitItem == '"' and not splitItem == "''" ):
           dialogValue=formJson["submission"][splitItem]


         value=value.replace("[" + str(splitItem) + "]" , str(dialogValue))

    self.app.logger.debug("Parse value=" +value)
    return(value)

  def parseDialog(self,dialog):

     elementIndex=-1
     for element in dialog["elements"]:

       elementIndex+=1
       if ( element["type"] == "select" and "value" in element and ":" in element["value"] ):

            dialogValue=element["value"]

            pos=dialogValue.index(":")
            commandType=dialogValue[:pos]
            value=dialogValue[pos+1:]
            #app.logger.debug(commandType + "," + value)

            ##run menu function
            if ( commandType == "function" ):
              output=functions.runFunction(value)
              element["options"]=output
              dialog[elementIndex]=element

     return(dialog)

  def saveMenuVars(self,menuItem):

    for item in menuItem:
      jsonItems=json.loads("menu/" + json.dumps(item))
      (key,value) = jsonItems.items()[0]
      slackDB=SlackDB(self.app)
      slackDB.set(key,value)


  def loadMenuStatus(self,menuName,selectName,slackUserName="",shared=False):
    self.app.logger.debug("loadMenu: {},{},{},{}".format(menuName , selectName, slackUserName,shared))

    menuData=[]
    dataFileName=""

    if ( shared == True ):
       dataFileName="menu/" + menuName + "_" + selectName + ".db"
    elif ( shared == False and not slackUserName == "" ):
       dataFileName="menu/" + menuName + "_" + selectName + "_" + slackUserName + ".db"

    self.app.logger.debug("loadMenuStatus filename: {}".format(dataFileName))
    if ( os.path.isfile(dataFileName ) ):
       fileObject = open(dataFileName ,'r')
       menuData = pickle.load(fileObject)
       fileObject.close()
       #self.app.logger.debug(menuData )
    return(menuData)


  def __saveObject(self,dataFileName,menuData,slackUserName):

    fileObject = open(dataFileName,'wb')
    pickle.dump(menuData,fileObject)
    fileObject.close()


  def saveMenuStatus(self,menuValue,menuName,selectName,selectType,slackUserName="",shared=False):
    self.app.logger.debug("saveMenu: {},{},{},{},{},{}".format(menuValue, menuName ,selectName , selectType , slackUserName,shared))

    menuData=self.loadMenuStatus(menuName,selectName,slackUserName,shared)
    self.app.logger.debug(menuData)
    if ( selectType == "multipule" and not menuValue in menuData ):
          menuData.append(menuValue)
    elif ( selectType == "unique" ):
          menuData=[menuValue]

    if ( not slackUserName == "" ):
      dataFileName="menu/" + menuName + "_"+ selectName + "_" + slackUserName + ".db"
      self.__saveObject(dataFileName,menuData,slackUserName)
   
    dataFileName="menu/" + menuName + "_"+ selectName + ".db"
    self.__saveObject(dataFileName,menuData,slackUserName)


  def clearMenuStatus(self,menuName,selectName,slackUserName="",shared=False):

    if ( shared == False and not slackUserName == "" ):
      dataFileName="menu/" + menuName + "_" + selectName + "_"+slackUserName+".db"
    else:
      dataFileName="menu/" + menuName + "_" + selectName + ".db"

    self.app.logger.debug("Clear menu select {}/{} {} {} {}".format(menuName,selectName,slackUserName,shared,dataFileName))
    if ( os.path.isfile(dataFileName ) ):
        self.app.logger.debug("clear menu " + dataFileName)
        os.remove(dataFileName)


  def getSlackUserName(self,formJson):
    if ( "user" in formJson ):
      return(formJson["user"]["name"])
    else:
      return("")


  def checkMenuRolesBeforeLoad(self,data,slackUserName):
    auth=Auth(self.app)
    
    options=[]
    self.app.logger.debug("checkMenuRolesBeforeLoad")
    self.app.logger.debug(slackUserName)
    self.app.logger.debug(data)

    if ( len(data) > 0 and "actions" in data[0] and "options" in data[0]["actions"][0] ):

       for option in data[0]["actions"][0]["options"]:

           if ( "roles" in option ):
             dataRoles=option["roles"]

             for role in dataRoles:
                if ( auth.checkUserInRole(slackUserName,role) ):
                   options.append(option)
                   break
           else:
             options.append(option)
              

       data[0]["actions"][0]["options"]=options

    return(data)


  def checkSelectedMenuRoles(self,menu,value,menuType,userName):
    self.app.logger.debug("loading roles: " + value + "," +  menuType + "," + userName)

    auth=Auth(self.app)
    roles=[]

    if  ( menuType == "select" ):
      for option in menu[0]["actions"][0]["options"]:
         if ( "value" in option and value == option["value"] and "roles" in option):
            roles=option["roles"]

    elif  ( menuType == "button" ):
      for button in menu[0]["actions"]:
            if ( "name" in button and value == button["name"] and "roles" in button ):
                roles=button["roles"]
            elif ( "value" in button and value == button["value"] and "roles" in button ):
                roles=button["roles"]

    if ( len(roles) == 0 ):
      return(True)

    self.app.logger.debug("roles calling auth")
    
    return(auth.checkUserInRoles(userName,roles))

