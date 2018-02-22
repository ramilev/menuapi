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

class SlackDB(object):

  def __init__(self,app):
    self.app=app
    self.dbFileName="slack_db.json"

    #self.__initDB()

    self.__loadDB()
    self.app.logger.debug(self.data)
 
  def __saveDB(self):
    self.app.logger.debug("saving db")
    with open(self.dbFileName, 'w') as dataFile:
      dataFile.write(json.dumps(self.data, dataFile,sort_keys=True,ensure_ascii=False))

  def __loadDB(self):
    self.app.logger.debug("loading db ")

    with open(self.dbFileName) as dataFile:
       data = json.load(dataFile)

    self.data=data

  def get(self,key):
    if ( key in self.data ):
      value=self.data[key]
    else:
      value=""

    self.app.logger.debug("getting from db "  + str(key) + ":" + str(value))
    return(value)

  def set(self,key,value):
    self.app.logger.debug("updating db "  + str(key) + ":" + str(value))
    self.data[key]=value
    self.__saveDB()
  

  def __initDB(self):
     self.data={
        "qa_approved": False,
        "product_approved": False,
        "started": False,
        "finished": False,
        "stories": "",
        "email": "",
        "release_manager_approved": False,
        "bluetogreen": False,
        "sanitypass": False,
        "admin_started": False,
        "admin_finished": False,
        "mvc_ver": "mvc_ver",
        "hour": 8,
        "time": False,
        "feature": "",
        "original_user": "",
        "ecs_sanitypass": False,
        "ecs_started": False,
        "ecs_finished": False,
 
     }
     self.__saveDB()
