"""
Cisco Meraki Location Scanning Data simulator

Default port: 5001

Matt DeNapoli

2018

https://developer.cisco.com/site/Meraki
"""

# Libraries
from pprint import pprint
from flask import Flask,json,request,render_template
import sys, getopt
import json
import random
import math
import datetime
import time
import requests

app = Flask(__name__)

#Globals
locationData = ''
mapBounds = ''
validator = ''
clientMacs = []
apMacs = []
apData = []
secret = ''
serverURL = ''


@app.route('/go', methods=['GET'])
def get_go():
    return render_template('index.html',**locals())

#get the bounds of the map so that the location data sticks within those bounds
@app.route('/bounds/<mapBoundsIn>', methods=['GET'])
def setLocationBounds(mapBoundsIn):
    global mapBounds    #Passed in from front-end js on update of map location

    mapBounds = mapBoundsIn
    mapBounds = mapBounds.replace('(','').replace(')','').replace(' ', '').split(',')

    return mapBounds


#generate FAKE MAC addresses for number of clients requested
def generateClientMacs(numClients, numAPs):
    global clientMacs

    for client in range(numClients):
        clientMac = ''
        for macPart in range(6):

            clientMac += ''.join(random.choice('0123456789abcdef') for i in range(2))

            if macPart < 5:
                clientMac += ':'
            else:
                clientMacs.append({'clientMac':clientMac,
                'associated':random.randint(0,1),
                'apassociated':random.randint(1,numAPs)})

def determineSeenAssociated():
    global clientMacs
    global apMacs
    random.shuffle(clientMacs)
    random.shuffle(apMacs)

    for client in clientMacs:
        client["associated"] = random.randint(0,1)
        client["apassociated"] = random.randint(1,len(apMacs));

    for ap in apMacs:
        ap["numAPClientsSeen"] = random.randint(1,len(clientMacs))


#generate FAKE MAC addresses for number of APs requested
def generateAPMacs(numAPs, numClients):
    global apMacs

    for ap in range(numAPs):
        apMac = ''
        for macPart in range(6):
            apMac += ''.join(random.choice('0123456789abcdef') for i in range(2))
            if macPart < 5:
                apMac += ':'
            else:
                apMacs.append({"apMac":apMac,"numAPClientsSeen":random.randint(1,numClients)})


#Kick off simulator and create baseline dataset
@app.route('/launchsimulator', methods=['POST'])
def generateLocationData():
    global validator
    global secret
    global serverURL
    global mapBounds
    global clientMacs
    global apMacs
    global apData

    validator = ''.join(random.choice('0123456789abcdef') for i in range(16))
    secret = request.form['secret']
    print(secret)
    numClients = int(request.form['numClients'])
    numAPs = int(request.form['numAPs'])
    serverURL = request.form['serverURL']

    deviceList = [{'os':'Android','manufacturer':'Samsung'},
        {'os':'iOS','manufacturer':'Apple'},
        {'os':'macOS','manufacturer':'Apple'},
        {'os':'Windows','manufacturer':'Lenovo'},
        {'os':'Linux','manufacturer':'Nest'},
        {'os':'Linux','manufacturer':'Amazon'}]
    dateTimeNow = datetime.datetime.now()
    epoch = (dateTimeNow - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000.0

    generateClientMacs(numClients,numAPs)
    generateAPMacs(numAPs,numClients)

    #generate the client distribution per ap
    #any ap may see all probing and associated clients
    #Only one ap may see an associated client
    for ap in apMacs:

        observations = []

        for seenClient in clientMacs:
            device = random.sample(deviceList, 1)
            device = device[0]
            ipv4 = None
            ssid = None
            if seenClient["associated"] == 1 and seenClient["apassociated"] == apMacs.index(ap):
                ipv4 = "192.168.0." + str(clientMacs.index(seenClient))
                ssid = "SimulatorWifi"

            observations.append({'clientMac': seenClient["clientMac"],
                'ipv4': ipv4,
                'ipv6': None,
                'location': {
                    'lat': random.uniform(float(mapBounds[0]),float(mapBounds[2])),
                    'lng': random.uniform(float(mapBounds[1]),float(mapBounds[3])),
                    'unc': random.uniform(0,10),
                    'x': [],
                    'y': []},
                    'manufacturer': device["manufacturer"],
                'os': device["os"],
                'rssi': random.randint(25,120),
                'seenEpoch': epoch,
                'seenTime': dateTimeNow.isoformat(sep='T', timespec='auto'),
                'ssid': ssid})

        apData.append({'data': {'apFloors': [],
                           'apMac': ap["apMac"],
                           'apTags': [],
                           'observations': observations},
                  'secret': secret,
                  'type': 'DevicesSeen',
                  'version': '2.0'})

    #Pass the AP array to cycle through them to
    apCycle(numAPs)


def updateLocationData(ap):
    global apData
    global mapBounds

    dateTimeNow = datetime.datetime.now()
    epoch = (dateTimeNow - datetime.datetime.utcfromtimestamp(0)).total_seconds() * 1000.0

    apInstance = apData[ap]

    observations = apInstance["data"]["observations"]

    for observation in observations:
        observation["location"]["lat"] = random.uniform(float(mapBounds[0]),float(mapBounds[2]))
        observation["location"]["lng"] = random.uniform(float(mapBounds[1]),float(mapBounds[3]))
        observation["location"]["unc"] = random.uniform(0,10)
        observation["rssi"] = random.randint(25,120)
        observation["seenEpoch"] = epoch
        observation["seenTime"] = dateTimeNow.isoformat(sep='T', timespec='auto')

    apInstance["data"]["observations"] = observations
    apData[ap] = apInstance
    print("updated ap ")
    print(apData[ap])

def postJSON(ap):
    global apData
    global serverURL
    requests.post(serverURL, json=apData[ap])
    print(apData[ap])

def apCycle(numAPs):
    ap = 0

    while True:
        print("heading to postJSON " + str(ap))
        postJSON(ap)
        print("back from postJSON " + str(ap))
        determineSeenAssociated()
        updateLocationData(ap)
        print("back from update" + str(ap))
        print("sleeping")
        time.sleep(10)
        print("done sleeping")
        if ap == numAPs-1:
            ap = 0
        else:
            ap += 1



if __name__ == '__main__':
    app.run(port=5001,debug=False)
