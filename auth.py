import pprint
import ConfigParser
import traceback
import sys,os,subprocess,time
import json
import re
from flask import Flask, request, make_response, Response
import pickle
import utils


#botHome="/myhubot/myhubot-rtb/scripts/"
botHome="."
dbFile="brain-dump.json"

class Auth(object):

  def __init__(self,app):
    self.app=app
    self.authData=utils.readJson(dbFile)


  def getUser(self,userName):

    for key,value in self.authData["users"].items():

      #self.app.logger.debug(key)
      #self.app.logger.debug(value)
      
      #if ( "slack" in value and "name" in value["slack"] and value["slack"]["name"] == userName ):
      if ( "name" in value and value["name"] == userName ):
         #self.app.logger.debug(value)
         return(value)
    return([])
     

  def checkUserExist(self,userName):

    userData=self.getUser(userName)

    if ( len(userData) ==  0 ):
       return(False)
    else:
       return(True)
  

  def checkUserAdmin(self,userName):
    
    userData=self.getUser(userName)
    if ( userData["slack"]["is_admin"] == True ):
       return(True)
    else:
       return(False)



  def checkUserInRole(self,userName,role):

    userRoles=self.__getUserRoles(userName)

    if ( role == None or userRoles == None ):
       return(False)

    if ( role in userRoles ):
       return(True)
    else:
       return(False)


  def checkUserInRoles(self,userName,roles):

    userRoles=self.__getUserRoles(userName)

    if ( userRoles == None ):
      return(False)

    for userRole in userRoles:
       
      self.app.logger.debug("Auth:" + userName + "," + userRole)
      if ( userRole in roles ):
         self.app.logger.debug("Auth ok:" + userName + "," + userRole)
         return(True)


    return(False)


  def __getUserRoles(self,userName):

    userData=self.getUser(userName)
    #self.app.logger.debug(userData["roles"])

    if ( "roles" in userData ):
      return(userData["roles"])
    else:
      return(None)


