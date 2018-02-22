# Slack menu

This library is Slack menus bot based on json files. The menus are selections lists and buttons that give users the ability to run any kind of flow and execute commands.

## Features 

- Menus and sub menus with navigation buttons  
- Multiple selections menu
- Fill menus using external functions
- Popup dialogs from menu selection
- Permissions and groups. 
- Remember last user choices
- execute external commands
- Python libraries for running Jenkins and Teletraan jobs 

## Getting started

- Copy directory content ( default /opt/slack )
- [Create Slack API App](Create Slack API App)
- Update slack.cfg with ```FLASK PORT``` and ```SLACK_BOT_TOKEN```
- If using systemd , update slack.service with application directory and copy slack.service to /etc/systemd/system
- Start server using ./slack_server.sh or ```systemctl start slack```
- Stop the server by killing slack_server.sh or ```systemctl stop slack```
  
## Create Slack API App

- Go to slack api apps https://api.slack.com/apps/ and create new application.
- Under Interactive Components, insert the Request URL ( ```http://<FLASK SERVER>:<FLASK_PORT>``` ). It should be the external server URL and FLASK port. ( Default FLASK PORT 4000 )
- Under install App , take "Bot User OAuth Access Token" and update slack.cfg ```SLACK_BOT_TOKEN```.
- Add bot user to channel
- From ```Slash Commands``` Add new slash command "/menu".
- From ```Install App``` install application to channel. 

## Prerequisites

  **Slack menu is written in Python and it depends on the following packages:**
  
- SlackClient
- gc
- Flask
- requests
- gc ( only for jenkins library )
- jenkins ( only for jenkins library )


## Menu file syntax

Menu files are json files in [Slack API format](https://api.slack.com)
All menu files located under menu folder and the main file is ***main.json*** .
Slack menu adds new attributes so it can add new feature to the menus and flow.

- ***callback_id:*** diveded into two parts from:current. From is the previous menu json file and current is the current menu json file. Example for sub menu under main menu-> ```main:sub_menu```
- ***title:*** Menu title
- ***footer:*** Display the menu path. Example for sub menu: Main ```menu->Sub Menu```
- ***type:*** ```Select``` is the menu list box and ```button``` is command button that excute the value
- ***shared:*** ```true/false``` how menu remember selections. If shared all users in channel will share the selection.
- ***functions:*** Fill menu list from python function. Slack server will search for the function in fuctions python module. Example of value attribute: ```"value" : "function:getExampleFunction"```. This will fill menu list by calling getExampleFunction.
- ***run:*** If value attribute includes run: it will run the command in background and display stdout to channel. Example: ```value": "run:./examples/example.sh test```
- ***exec:*** Same as run but will not display stdout to channel.
- ***exec_gomain:*** Same as exec but after running the command, it will display the main menu (main.json)
- ***exec_gomenu-menu name:*** After executing the command, it will display the choosen menu.
- ***dialog:*** Open popup dialog. ```"value": "dialog:dialog_example"```. Dialog file name is ```dialog_example.json```
- ***roles:*** Enable to select menu value only for groups. ```"roles": ["devops","dev"]```. Users and groups fie definition: ```brain-dump.json```. Auth python object can be changed to use Ldap instead of json file. 

## Reserved words

- ***[PAYLOAD]*** The Slack POST payload json. This can be used as an argument so modules can get Slack source attributes and values such as channel and user.
- ***[menu_file_name:menu_select_name]*** Flask server will replace the choosen value in the menu name and the select list name and pass it as an argument. 

## Running Jenkins jobs
slack_jenkins.py can be used to trigger jenkins jobs and update Slack channel with its status.
Ths module can be called as executable or as Python object.

Cli usage:

```
slack_jenkins.py <channel name> <job name> [json parameters]
```

Python object usage: 

```
parameters={"param1_name": "param1_value" , "param2_name": "param2_value" }
slackJenkins=SlackJenkins(channel,buildJobName,parameters)
buildNumber=slackJenkins.buildJob()
jobStatus=slackJenkins.getJobStatus(buildNumber)
```


## Examples

###Sub Menu Example

```
[{
        "fallback": "Slack Error , contact Devops.",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "response_type": "in_channel",
        "replace_original": true,
        "callback_id": "main:sub_menu",
        "title" : "Sub menu example",
        "text" : " ",
        "footer" : "Main->Sub Menu",
        "shared": true,
        "actions":
          [
            {
                "name": "menu",
                "text": "Choose",
                "type": "select",
                "options": [
                        {
                            "text": "Sub Menu Bash example",
                            "value": "run:./examples/example.sh test \"[main:menu]\""
                        },
                        {
                            "text": "Sub Menu Python example",
                            "value": "exec:./examples/example.py \"[PAYLOAD]\""
                        },
                        {
                            "text": "Sub Menu Dialog example",
                            "value": "dialog:dialog_example"
                        }

                ]

            },

                        {
                            "name": "back",
                            "text": "Back",
                            "type": "button",
                            "value": "back",
                            "style": "primary"
                        },
                        {
                            "name": "main",
                            "text": "Main",
                            "type": "button",
                            "value": "main",
                            "style": "primary"
                        }
          ]
     }
    ]   
 
```
    
### Multi select menu
    
```
         [{
        "fallback": "Slack Error , contact Devops.",
        "color": "#3AA3E3",
        "attachment_type": "default",
        "callback_id": "main:multi_select",
        "text" : " ",
        "title" : "Multi select menu",
        "response_type": "in_channel",
        "replace_original": true,
        "mrkdwn_in": ["text", "pretext"],
        "selectType": "multipule",
        "footer" : "Main->Multi select menu",
        "save": "value",
        "shared" : true,
        "actions":
          [
                        {
                            "name": "selections",
                            "text": "Choose service",
                            "type": "select",
                            "min_query_length": 5,
                            "options": [
                              {
                                "text": "selection 1",
                                "value": "selection_1"
                              },
                              {
                                "text": "selection 2",
                                "value": "selection_2"
                              },
                              {
                                "text": "selection 3",
                                "value": "selection_3"
                              },
                              {
                                "text": "selection 4",
                                "value": "selection_4"
                              }
                            ]
                        },
                        {
                            "name": "clear",
                            "text": "clear",
                            "type": "button",
                            "value": "clearSelect:services"
                        },
                        {
                            "name": "submit",
                            "text": "Submit",
                            "type": "button",
                            "value": "exec_gomain:./examples/example_multi_select.py \"[PAYLOAD]\" [multi_select:selections]",
                            "style": "danger"
                        },
                        {
                            "name": "back",
                            "text": "Back",
                            "type": "button",
                            "value": "back",
                            "style": "primary"
                        },
                        {
                            "name": "main",
                            "text": "Main",
                            "type": "button",
                            "value": "main",
                            "style": "primary"

          ]
     }
    ]
    
```

