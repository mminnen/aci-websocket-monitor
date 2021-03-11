#!/usr/local/bin/python

import json
import time
import ssl
import sys
# import os


from pathlib import Path
from os import path as ospath

from flask import Flask

app = Flask(__name__)

## Every Function/Service Must contain a /ready path. 
## Knative uses this to know when your container is ready to go.
@app.route('/ready')
def ready():
   return 'ready'

@app.route('/')
def index():
    # time.sleep(10)
    return 'Refreshed, for 30 seconds'

# Variables for input and output data
pathConfig = "/home/config/config.yml"
pathApicLoginTemplate = "/home/templates/apicLoginTemplate.json"
pathSubscriptionIds = "/home/internal/subscriptionIds.json"
basePathLogs = "/home/data/logs/"
basePathOutput = "/home/data/output/"
loginToken = ""

# Load config file, it is required in multiple follwing functions
with open(pathConfig, "r") as handle:
    config = yaml.full_load(handle)

# Disable warning for APIC Self-Signed Certificate
requests.packages.urllib3.disable_warnings()

# Write Tool logs to local logfile, can be mapped to host volume
# Messages are provided by the calling functions
def writeLog(message):
    Path(basePathLogs).mkdir(parents=True, exist_ok=True)
    logPath = basePathLogs + time.strftime('%Y-%m-%d', time.localtime()) + ".txt"
    timestamp = time.strftime("%d/%m/%Y-%H:%M:%S", time.localtime())

    old_stdout = sys.stdout
    sys.stdout = open(logPath,"a+")
    print(timestamp)
    print(message)
    sys.stdout.close()
    sys.stdout = old_stdout

def outputToRest(message):
    print('webhook received')
    toRest = config['data_output']['toRest']

    # Check for HTTP/HTTPS and optional Destination Port
    if toRest['ssl'] is True and "destPort" in toRest:
        url = "https://" + toRest['destAddress'] + ":" + toRest['destPort']
    elif toRest['ssl'] is True:
        url = "https://" + toRest['destAddress']
    if toRest['ssl'] is False and "destPort" in toRest:
        url = "http://" + toRest['destAddress'] + ":" + toRest['destPort']
    else:
        url = "http://" + toRest['destAddress']

    # REST Call with Basic Auth (if configured)
    if "username" in toRest and "password" in toRest:
        response = requests.post(
            url,
            headers = {'Content-Type': 'application/json'},
            auth=(toRest['username'], toRest['password']),
            data = json.dumps(json.JSONDecoder().decode(message))
        )
    
    elif "username" in toRest and not "password" in toRest:
        log = "You must provide both Username and Password for Authentication! Falling back to No Auth."
        writeLog(log)
        return False

    elif not "username" in toRest and "password" in toRest:
        log = "You must provide both Username and Password for Authentication! Falling back to No Auth."
        writeLog(log)
        return False

    # REST Call with No Auth (if none configured)
    else:
        response = requests.post(
            url,
            headers = {'Content-Type': 'application/json'},
            data = json.dumps(json.JSONDecoder().decode(message))
        )

    return True

def outputToFile(message):
    toFile = config['data_output']['toFile']

    baseList = []

    Path(basePathOutput).mkdir(parents=True, exist_ok=True)
    outputPath = basePathOutput + toFile['baseFilename'] + "_" + time.strftime('%Y-%m-%d', time.localtime()) + ".json"

    if ospath.exists(outputPath):
        with open(outputPath, "r") as handle:
            baseList = json.load(handle)

        baseList.append(json.JSONDecoder().decode(message))

    else:
        baseList.append(json.JSONDecoder().decode(message))

    old_stdout = sys.stdout
    sys.stdout = open(outputPath,"w+")
    print(json.dumps(baseList))
    sys.stdout.close()
    sys.stdout = old_stdout

    return True

def apicLogin():

    with open(pathApicLoginTemplate, "r") as handle:
        apicLoginTemplate = json.load(handle)

    apicLoginTemplate['aaaUser']['attributes']['name'] = config['apic_login']['username']
    apicLoginTemplate['aaaUser']['attributes']['pwd'] = config['apic_login']['password']

    response = requests.post(
            'https://' + config['apic_login']['address'] + '/api/aaaLogin.json',
            headers = {'Content-Type': 'application/json'},
            data = json.dumps(apicLoginTemplate),
            verify = False
    )

    responseDict = json.loads(response.text)
    token = responseDict['imdata'][0]['aaaLogin']['attributes']['token']

    message = "APIC Login successful."
    writeLog(message)

    return token

def subscribe(loginToken):
    subIds = []

    if not config['monitored_objects']:
        response = requests.get(
            "https://" + config['apic_login']['address'] + "/api/node/class/faultInst.json?subscription=yes&refresh-timeout=600",
            headers = {'Cookie': "APIC-cookie=" + loginToken},
            verify = False
        )
        subIds.append(json.loads(response.text)['subscriptionId'])
    else:
        for sub in config['monitored_objects']:
            response = requests.get(
                "https://" + config['apic_login']['address'] + sub + ".json?subscription=yes&refresh-timeout=600",
                headers = {'Cookie': "APIC-cookie=" + loginToken},
                verify = False
            )
            subIds.append(json.loads(response.text)['subscriptionId'])

    message = "Subscription successful. Subscription IDs:\n"
    for subid in subIds:
        message = message + subid + "\n"
    writeLog(message)

    with open(pathSubscriptionIds, "w") as handle:
        json.dump(subIds, handle)

def refresh():

    while True:
        time.sleep(540)

        with open(pathSubscriptionIds, "r") as handle:
            subscriptionIds = json.load(handle)

        loginToken = apicLogin()

        message = "Subscription Refresh successful. Refreshed subscription IDs: \n"
        for sub in subscriptionIds:
            response = requests.get(
                "https://" + config['apic_login']['address'] + "/api/subscriptionRefresh.json?id=" + sub,
                headers = {'Cookie': "APIC-cookie=" + loginToken},
                verify = False
            )
            if not json.loads(response.text)['imdata']:
                message = message + sub + "; "
            else:
                message = message + "Subcription " + sub + " could not be refreshed.\n"

        writeLog(message)

def on_message(ws, message):

    if "toRest" in config['data_output']:
        outputToRest(message)

    if "toFile" in config['data_output']:
        outputToFile(message)

def on_error(ws, error):
    writeLog(error)

def on_close(ws):
    os.remove(pathSubscriptionIds)
    message = "Socket was closed."
    writeLog(message)

def on_open(ws):
    subscribe(loginToken)

if __name__ == "__main__":
    loginToken = apicLogin()

    refreshThread = threading.Thread(target=refresh)
    refreshThread.start()

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://" + config['apic_login']['address'] + "/socket" + loginToken,
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close,
                                on_open = on_open)

    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
    
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8000)))
