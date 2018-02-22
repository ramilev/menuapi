#!/usr/bin/python

import jenkins
import sys
import time
import consul
import boto3

from slack_config import SlackConfig
from slackclient import SlackClient
import utils


consulUrls={ "like": "consul-like.matomy.local" , "prod": "consul.matomy.local" }

slackConfig=SlackConfig()
SLACK_BOT_TOKEN = slackConfig.get("SLACK_BOT_TOKEN")
slack_client = SlackClient(SLACK_BOT_TOKEN)

class EcsStatus(object):

    def __init__(self,env,formJson):

        self.awsAccessKeyId = ""
        self.awsSecretAccessKey = ""
        self.env=env
        self.__getAwsKeys()
        self.ecsClient = boto3.client('ecs',region_name="us-east-1", aws_access_key_id=self.awsAccessKeyId, aws_secret_access_key=self.awsSecretAccessKey)
        self.ec2Client = boto3.client('ec2',region_name="us-east-1", aws_access_key_id=self.awsAccessKeyId, aws_secret_access_key=self.awsSecretAccessKey)
        self.ec2Resource = boto3.resource('ec2',region_name="us-east-1", aws_access_key_id=self.awsAccessKeyId, aws_secret_access_key=self.awsSecretAccessKey)

        index, data = self.consul.kv.get(self.env + "/ecs/cluster_name")
        self.cluster=str(data["Value"])

        self.channel=formJson["channel"]["name"]
        self.channelId=formJson["channel"]["id"]


    def __getAwsKeys(self):

        self.consul = consul.Consul(host=consulUrls[self.env] , port=8500, scheme='http')
        index, data = self.consul.kv.get(self.env + "/ecs/aws_access_key_id")
        self.awsAccessKeyId=str(data["Value"])
        index, data = self.consul.kv.get(self.env + "/ecs/aws_secret_access_key")
        self.awsSecretAccessKey=str(data["Value"])


    def status(self):
        #response = self.ecsClient.describe_clusters(clusters=[self.cluster]) 

        #print "{:^60}".format("*                    " + self.env + " Microservices Status*")
        #print ("*-" * 55 + "*")
        containerInstances = self.ecsClient.list_container_instances(cluster=self.cluster) 
        instances=self.ecsClient.describe_container_instances(cluster=self.cluster,containerInstances=containerInstances["containerInstanceArns"])

        
        fields=[]
        for container in containerInstances["containerInstanceArns"]:

          for instance in instances["containerInstances"]:
            
            if ( container == instance["containerInstanceArn"] and not self.ec2Resource.Instance(instance["ec2InstanceId"]).private_ip_address == None ):
             
              #print "*Instance IP:* `" + self.ec2Resource.Instance(instance["ec2InstanceId"]).private_ip_address + "`"
              instanceIp=self.ec2Resource.Instance(instance["ec2InstanceId"]).private_ip_address
              #sys.stdout.write("*Services:* \n")

              tasksList=self.ecsClient.list_tasks(cluster=self.cluster,containerInstance=container,desiredStatus="RUNNING")
              if ( len(tasksList["taskArns"]) > 0 ):
                tasks=self.ecsClient.describe_tasks(cluster=self.cluster,tasks=tasksList["taskArns"])

                index=0
                services=""
                while index<len(tasks["tasks"]):
                   #sys.stdout.write("`" + tasks["tasks"][index]["containers"][0]["name"] + "`\n")
                   services=services+tasks["tasks"][index]["containers"][0]["name"] + "\n"
                   index+=1

                fields.append ( { "title" : instanceIp , "value": services, "short": True } )


        attachments = [
                  {
                   "attachment_type": "default",
                   "text" : "",
                   "title": "ECS " + self.env,
                   "unfurl_media": False,
                   "short": True,
                   "mrkdwn_in": ["text", "title"],
                   "fields" : fields
                 }
        ]


        response = slack_client.api_call(
                  "chat.postMessage",
                  channel=self.channelId,
                  mrkdwn=True,
                  attachments=attachments
        )


def main():

   if ( len(sys.argv) < 2 ):
      print "Usage: <payload>"
      sys.exit()

   formJson=utils.parseJson(sys.argv[1])

   print ">>>"
   ecsStatus=EcsStatus("like",formJson)
   ecsStatus.status()

   ecsStatus=EcsStatus("prod",formJson)
   ecsStatus.status()


if __name__ == '__main__':
  main()


