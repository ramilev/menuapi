#!/usr/bin/python

import pprint
import sys,os,subprocess,time
import consul
import ConfigParser

scriptDir=os.path.dirname(os.path.realpath(__file__))
configFile="slack.cfg"

class SlackConfig(object):

  def __init__(self):

    self.config = ConfigParser.RawConfigParser()
    self.config.read(scriptDir + "/" + configFile)

  def get(self,keyName,section="slack"):

    value=self.config.get(section,keyName)
    return(value)
