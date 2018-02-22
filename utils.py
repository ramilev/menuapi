import pprint
import ConfigParser
import traceback
import sys,os,subprocess,time
import json
import re
from flask import Flask, request, make_response, Response
import pickle
import datetime
import time

def runCmd(cmd):

    buffer=""
    print "cmd=" + cmd
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for line in p.stdout.readlines():
                buffer=buffer + line
    status = p.wait()

    return(buffer,status)


def readJson(fileName):

    if ( os.path.isfile(fileName) ):
      with open(fileName) as dataFile:
         data = json.load(dataFile)
    else:
      data={}

    return(data)

def parseJson(jsonString):
   jsonString=jsonString.replace("u\'","\'")
   jsonString=jsonString.replace("\'","\"")
   jsonString=jsonString.replace("False","false")
   jsonString=jsonString.replace("True","true")
   jsonString=json.loads(jsonString)
   return(jsonString)


def sendEmail(subject,msg):
   print "sending mail "
   #'mailx', ["-r", "rtb-rnd@matomy.com", "-s", subject, "rtb-rnd@matomy.com"], {}, (error, stdout, stderr)
   #p.stdin.write "#{msg}"
   #p.stdin.end()


def convertToDate(epochTime):
   if ( epochTime > 1000000000000 ):
     return(int(time.strftime("%Y%m%d", time.gmtime(epochTime/1000.))))
   else:
     return(int(time.strftime("%Y%m%d", time.gmtime(epochTime))))


def convertTime(epochTime):
   if ( epochTime > 1000000000000 ):
     return(int(time.strftime("%Y%m%d%H%M", time.gmtime(epochTime/1000.))))
   else:
     return(int(time.strftime("%Y%m%d%H%M", time.gmtime(epochTime))))



def convertDisplayTime(epochTime):

   if ( epochTime > 1000000000000 ):
     return(str(time.strftime("%d/%m/%y-%H:%M", time.gmtime(epochTime/1000.))))
   else:
     return(str(time.strftime("%d/%m/%y-%H:%M", time.gmtime(epochTime))))


def daysCompare(epochTime):

   if ( epochTime == None or epochTime == 0 ):
      return(999999999)

   if ( epochTime > 1000000000000 ):
       epochTime=epochTime/1000

   currentTime=int(time.time())
   days = ( currentTime - epochTime ) / 86400

   return(days)
