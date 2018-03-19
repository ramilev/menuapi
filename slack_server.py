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
from threading import Thread
from slack_config import SlackConfig


slackConfig=SlackConfig()
SLACK_BOT_TOKEN = slackConfig.get("SLACK_BOT_TOKEN")
rootMenuUrl=slackConfig.get("root_menu_url")

# Slack client for Web API requests
slack_client = SlackClient(SLACK_BOT_TOKEN)

# Flask webserver for incoming traffic from Slack
app = Flask(__name__)
homeDir=os.path.dirname(os.path.realpath(__file__))

mainMenu="main"


class SlackMenu(object):


  def __init__(self):

     self.slack=Slack(app)
     self.auth=Auth(app)
     self.slackDB=SlackDB(app)
     self.shared=False


  #main menu
  def menu(self,request):

    app.logger.debug("in main menu")
    app.logger.debug(request.form)

    if ( "trigger_id" in request.form ):
       trigger_id=request.form["trigger_id"]
    else:
       trigger_id=""

    if ( "payload" in request.form ):

      formJson = json.loads(request.form["payload"])
      channel=formJson["channel"]["id"]
      if ( formJson["actions"][0]["type"] == "select" ):
        app.logger.debug(formJson["actions"][0]["selected_options"][0]["value"])

    else:
       formJson = request.form
       channel=formJson["channel_id"]
      
    menu=utils.readJson("menu/" + mainMenu + ".json")

    slackUserName=formJson["user_name"]
    self.slackUserName=slackUserName

    if ( not "User " in menu[0]['title'] ):
      menu[0]['title']="User " + slackUserName + "\n" + menu[0]['title']

    message_attachments = menu
    app.logger.debug(menu[0]['text'])
    
    response = slack_client.api_call(
      "chat.postMessage",
      channel=channel,
      attachments=message_attachments
    )

    app.logger.debug(response)

    return make_response("", 200)


  def __saveMenu(self,menuName,selectName,value):

    app.logger.debug("Saving menu " + menuName + ",selectName=" + selectName + ",value=" + value)

    selectType="unique"
    text=""

    if ( os.path.isfile("menu/" + menuName + ".json") ):
         menu=utils.readJson("menu/" + menuName + ".json")

         for item in menu[0]["actions"][0]["options"]:
            #app.logger.debug("Menu text: " + item["text"])

            if ( "save" in item ):
               slack.saveMenuVars(item["save"])

            if ( "value" in item and item["value"] == value ):
               text=item["text"]

            #app.logger.debug("Menu text: " + item["text"])

         if ( text == "" ):
            text=value 

         if ( "selectType" in menu[0] ):
            selectType=menu[0]["selectType"]

         #save value
         if ( "save" in menu[0] and menu[0]["save"] == "value" ):
            text=value 

         #save text
         #elif ( "save" in menu[0] and menu[0]["save"] == "text" ):
         #   text=item["text"]


    app.logger.debug("Menu selectType: " + selectType)
    app.logger.debug("Menu text: " + text)
    app.logger.debug("Menu value: " + value)


    if ( "name" in self.formJson["actions"][0] ):
       slack.saveMenuStatus(text,menuName , selectName ,selectType,self.slackUserName, self.shared )


  #clear saved selected values
  def __clearSelect(self,value):

       slack.clearMenuStatus(self.previousMenuName,value,self.slackUserName,self.shared)
       menuData=""

       originalMessage=self.formJson["original_message"]
       attachments=originalMessage["attachments"]

       attachments[0]["mrkdwn_in"]=["text", "pretext","fields"]
       attachments[0]["text"]=" "
       if ( not "User " in attachments[0]["title"] ):
         attachments[0]["title"]="User " + self.slackUserName + "\n" + attachments[0]['title']

       response = slack_client.api_call(
        "chat.update",
        channel=self.channel,
        ts=self.formJson["message_ts"],
        #thread_ts=self.formJson["message_ts"],
        attachments=attachments
       )


  #menu value selected and no menu json file
  def __processSelected(self,commandType,value,selectName):

       app.logger.debug("Menu: " + commandType + "," + self.previousMenuName + "," + value)

       #check for defult_submit in previous menu
       if ( self.previousMenu[0]["actions"][0]["type"] == "select" and "default_submit" in self.previousMenu[0]["actions"][0] ):
           app.logger.debug("Found default submit:" + self.previousMenu[0]["actions"][0]["default_submit"])
           defaultSubmit=self.previousMenu[0]["actions"][0]["default_submit"]  
           pos=defaultSubmit.index(":")

           commandType=defaultSubmit[:pos]
           value=defaultSubmit[pos+1:]
           value=slack.parseMenuValue(value,self.formJson,self.slackUserName)

           app.logger.debug("commadtype:" + commandType + ",value:" + value)

           if ( "exec_gomenu" in commandType or "run_gomenu" in commandType or commandType == "exec_gomain" or commandType == "run_gomain" or commandType == "exec_goback" or commandType == "run_goback" ): 
             self.__runExternal(commandType,value,self.previousMenu[0]["footer"])
             return
           else:
             self.__loadMenu(commandType,value,selectName)
             return
 
       menuData=slack.loadMenuStatus(self.previousMenuName,selectName,self.slackUserName, self.shared)

       textData=""
       for data in menuData:
         if not textData == "" :
            textData+=","
         textData += data

       originalMessage=self.formJson["original_message"]
       attachments=originalMessage["attachments"]

       attachments[0]["mrkdwn_in"]=["text", "pretext","fields"]
       attachments[0]["text"]="Last Selected: " + textData
       if ( not "User " in attachments[0]["title"] ):
          attachments[0]["title"]="User " + self.slackUserName + "\n" + attachments[0]['title']

       response = slack_client.api_call(
        "chat.update",
        channel=self.channel,
        ts=self.formJson["message_ts"],
        #thread_ts=self.formJson["message_ts"],
        attachments=attachments
       )

  #run external script
  def __runExternal(self,commandType,value,footer):

       cmd=value
       cmdArgs=cmd.split(" ")

       if ( "run" in commandType ):
         response = slack_client.api_call(
          "chat.postMessage",
          channel=self.channel,
          ts=self.formJson["message_ts"],
          text="*User* `" + self.slackUserName + "`\n*Running command:* " + cmdArgs[0] + " \n*From menu:* " + footer
         )
      

       thr = Thread(target=self.__slackThreadRun , args=[cmd,commandType])
       thr.start()

       if ( commandType == "exec_nomenu" ):
          return
       #load menu after running
       elif commandType == "exec_gomain" or commandType == "run_gomain":
         #load main menu
         menuName=mainMenu
       elif commandType == "exec_goback" or commandType == "run_goback":
         #load previous menu
         menuName=self.callbackMenuName
       elif "exec_gomenu" in commandType or "run_gomenu" in commandType:
         pos=commandType.index("-")
         menuName=commandType[pos+1:]

       else:
         #load current menu
         menuName=self.previousMenuName


       menu=utils.readJson("menu/" + menuName + ".json")
       if ( not "User " in menu[0]["title"] ):
         menu[0]["title"]="User " + self.slackUserName + "\n" + menu[0]['title']

       menu=self.__loadSelectedValues(menu,menuName)
       app.logger.debug(menu)

       if ( "exec_gomenu" in commandType or "run_gomenu" in commandType) :

          menu=self.__loadSelectedValues(menu,menuName)

          response = slack_client.api_call(
           "chat.update",
           channel=self.channel,
           ts=self.formJson["message_ts"],
           attachments=menu
          )
       else:
          response = slack_client.api_call(
           "chat.postMessage",
           channel=self.channel,
           attachments=menu
          )


  #check selected option permissions
  def __checkMenuPermissions(self,selectValue):

      userHasRoles=slack.checkSelectedMenuRoles(self.previousMenu,selectValue,"select",self.slackUserName)
      if ( not userHasRoles ):
        response = slack_client.api_call(
          "chat.postMessage",
          channel=self.channel,
          text="*Alert*: `You dont have permission for that operation!`"
        )
        return(False)

      return(True)
 
  def __loadSelectedValues(self,menu,menuName):

      selectName=menu[0]["actions"][0]["name"]
      menuData=slack.loadMenuStatus( menuName, selectName, self.slackUserName , self.shared )

      textData=""
      for menuItem in menuData:
        if not textData == "" :
            textData+=","
        textData += menuItem

      if ( not textData  == "" ):
            menu[0]["text"]="Last Selected: " + textData

      return(menu)
 

  #load menu selection from json
  def __loadMenu(self,commandType,value,selectName):

       app.logger.debug("__loadMenu:" + commandType + "," + value + "," + selectName + "," + self.slackUserName)
       menuName=value
       menu=utils.readJson("menu/" + menuName + ".json")

       #check menu roles before display
       menu=slack.checkMenuRolesBeforeLoad(menu,self.slackUserName)
       app.logger.debug(menu)

       #check for special values in menu
       if ( "actions" in menu[0] and "value" in menu[0]["actions"][0] ):

         menuValue=menu[0]["actions"][0]["value"]
         if ( ":" in menuValue ):

            pos=menuValue.index(":")
            commandType=menuValue[:pos]
            value=menuValue[pos+1:]
            app.logger.debug(commandType + "," + value)

            #run menu function
            if ( commandType == "function" ):
              function=slack.parseMenuValue(value,self.formJson,self.slackUserName)
              #function=value.encode('utf-8') + "()"
              #output=eval(function)
              app.logger.debug(function)
              output=functions.runFunction(function)
              menu[0]["actions"][0]["options"]=output


       #load menu saved data
       if ( "actions" in menu[0] and "name" in menu[0]["actions"][0] ):
         menu=self.__loadSelectedValues(menu,menuName)

       #display the menu
       app.logger.debug(menu)
       if ( not "User " in menu[0]["title"] ):
          menu[0]["title"]="User " + self.slackUserName + "\n" + menu[0]['title']

       response = slack_client.api_call(
        "chat.update",
        channel=self.channel,
        thread_ts=self.formJson["message_ts"],
        ts=self.formJson["message_ts"],
        attachments=menu
       )


  #dialog
  def __dialog(self,value):

       #dialog submited
       if ( value == "" and "submission" in self.formJson):
         dialog=utils.readJson("menu/" + self.previousMenuName + ".json")
         app.logger.debug(dialog)

         #check if there submit command
         if ( "value" in dialog and ( "run" in dialog["value"] or "exec" in dialog["value"] )):
           value=dialog["value"]

           pos=value.index(":")
           commandType=value[:pos]
           cmd=value[pos+1:]
           cmdArgs=value.split(" ")


           cmd=slack.parseDialogValue(cmd,self.formJson)
           response = slack_client.api_call(
             "chat.postMessage",
             channel=self.channel,
             text="*User* `" + self.slackUserName + "`\n*Running command:* " + cmdArgs[0]
           )
 
           thr = Thread(target=self.__slackThreadRun , args=[cmd,commandType])
           thr.start()

           #load menu after running
           if commandType == "exec_gomain" or commandType == "run_gomain":
              #load main menu
              menuName=mainMenu
           else:
              #load current menu
              menuName=self.callbackMenuName

         
           menu=utils.readJson("menu/" + menuName + ".json")
           if ( not "User " in menu[0]["title"] ):
              menu[0]["title"]="User " + self.slackUserName + "\n" + menu[0]['title']

           response = slack_client.api_call(
             "chat.postMessage",
             channel=self.channel,
             attachments=menu
           )
           app.logger.debug(response)

       else:
         #show dialog
         dialog=utils.readJson("menu/" + value + ".json")
         dialog=slack.parseDialog(dialog)

         response = slack_client.api_call(
           "dialog.open",
           channel=self.channel,
           trigger_id=self.triggerId,
           dialog=dialog
         )

         app.logger.debug(response)



  #menu options
  def menuProcess(self,request):

    app.logger.debug("in index")
    app.logger.debug(request.form)

    self.request=request
    commandType="menu"
    callback=""
    self.previousMenuName=""
    self.callbackMenuName=""
    roles=[]
    footer=""
    value=""
    self.channel=""
    self.ts=""

    self.formJson = json.loads(request.form["payload"])
    self.slackUserName=slack.getSlackUserName(self.formJson)

    if ( "trigger_id" in self.formJson ):
       self.triggerId=self.formJson["trigger_id"]
    else:
       self.triggerId=""

    self.channel=self.formJson["channel"]["id"]
    if ( "message_ts" in self.formJson ):
      self.ts=self.formJson["message_ts"]

    if ( "callback_id" in self.formJson ):
       self.callbackMenuName=self.formJson["callback_id"].split(":")[0]
       self.previousMenuName=self.formJson["callback_id"].split(":")[1]

    if ( "submission" in self.formJson and "type" in self.formJson and self.formJson["type"] == "dialog_submission" ):
       commandType="dialog"

    #load callback menu data
    callbackMenu=utils.readJson("menu/" + self.callbackMenuName + ".json")

    #load previous menu data
    self.previousMenu=utils.readJson("menu/" + self.previousMenuName + ".json")
    app.logger.debug(self.previousMenu)

    if ( isinstance(self.previousMenu , list) and len(self.previousMenu) > 0 and  "footer" in self.previousMenu[0] ):
       footer=self.previousMenu[0]["footer"]

    if ( isinstance(self.previousMenu , list) and not self.previousMenu == {} and "name" in self.previousMenu[0]["actions"][0] ):
      selectName=self.previousMenu[0]["actions"][0]["name"]
    else:
      selectName=""

    if ( isinstance(self.previousMenu , list) and len(self.previousMenu) > 0 and "shared" in self.previousMenu[0] ):
      self.shared=self.previousMenu[0]["shared"]

    if ( "actions" in self.formJson and self.formJson["actions"][0]["type"] == "select" ):

      selectValue=self.formJson["actions"][0]["selected_options"][0]["value"]

      if ( "save:" in selectValue ):
         commandType="menu"
         values=selectValue.split(":")
         value=values[2]
         selectValue=values[1]

      elif ( ":" in selectValue ):
         pos=selectValue.index(":")
         commandType=selectValue[:pos]
         value=selectValue[pos+1:]
      else:
         value=selectValue
 

      if ( self.__checkMenuPermissions(selectValue) == False ):
         return make_response("", 200)

      self.__saveMenu(self.previousMenuName,selectName,selectValue)


    if ( "actions" in self.formJson and self.formJson["actions"][0]["type"] == "button" ):

      buttonValue=self.formJson["actions"][0]["value"]
      buttonName=self.formJson["actions"][0]["name"]
      userHasRoles=slack.checkSelectedMenuRoles(self.previousMenu,buttonName,"button",self.slackUserName)
      if ( not userHasRoles ):
        response = slack_client.api_call(
          "chat.postMessage",
          channel=self.channel,
          text="@" + self.slackUserName + " *Alert*: `You dont have permission for that operation!`"
        )
        return make_response("", 200)


      if ( ":" in buttonValue ):
         pos=buttonValue.index(":")
         commandType=buttonValue[:pos]
         value=buttonValue[pos+1:]
      elif ( buttonValue == "back" ):
         commandType="menu"
         value=self.callbackMenuName
      elif ( buttonValue == "main" ):
         commandType="menu"
         value=mainMenu
      else:
         value=buttonValue


    value=slack.parseMenuValue(value,self.formJson,self.slackUserName,self.shared)
    app.logger.debug("Post data:" + commandType + "," + value)


    #load menu selection from json
    if ( commandType == "menu" and os.path.isfile( "menu/" + value + ".json" ) ):

       self.__loadMenu(commandType,value,selectName)

    #dialog
    elif ( commandType == "dialog" ):
       self.__dialog(value)

    elif ( commandType == "clearSelect" ):
       self.__clearSelect(value)


    #menu value selected and no menu json file
    elif ( commandType == "menu" and not os.path.isfile( "menu/" + value + ".json" ) ):

       self.__processSelected(commandType,value,selectName)

    #run external script
    elif ( "run" in commandType or "exec" in commandType ):

       self.__runExternal(commandType,value,footer)

    return make_response("", 200)
 

  #running command in background thread
  def __slackThreadRun(self,cmd,commandType):

       status=0
       (output,status)=utils.runCmd(cmd)
       output=str(output).replace("\\n","\n")

       if ( "run" in commandType ):

         if ( status == 0 ):
           output+=":white_check_mark: *Submit command finished successfully*"
         else:
           output+=":x: *Submit command Failed*"

         response = slack_client.api_call(
           "chat.postMessage",
           channel=self.formJson["channel"]["id"],
           text=output
         )

       return
       #load menu after running
       if commandType == "exec_gomain" or commandType == "run_gomain":
         #load main menu
         menuName=mainMenu
       elif commandType == "exec_goback" or commandType == "run_goback":
         #load previous menu
         menuName=self.callbackMenuName
       else:
         #load current menu
         menuName=self.previousMenuName

       menu=utils.readJson("menu/" + menuName + ".json")
       menu[0]['title']="User " + self.slackUserName + "\n" + menu[0]['title']
       app.logger.debug(menu)

       response = slack_client.api_call(
           "chat.postMessage",
           channel=self.formJson["channel"]["id"],
           attachments=menu
       )


@app.route('/menu',methods=["POST"])
def menu():

    slackMenu.menu(request)
    return make_response("", 200)



@app.route('/',methods=["POST"])
def index():

    slackMenu.menuProcess(request)
    return make_response("", 200)


@app.route('/external',methods=["POST"])
def external():
    app.logger.debug("in external")
    app.logger.debug(request.form["payload"])

    menu_options={}
    return Response(json.dumps(menu_options), mimetype='application/json')


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    func()

@app.route('/shutdown', methods=['POST','GET'])
def shutdown():
    shutdown_server()
    return 'Server shutting down...'

#------------------------- Main ----------------------------------


slackMenu=SlackMenu()
slack=Slack(app)

