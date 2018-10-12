#!/usr/bin/python

import subprocess, platform
from datetime import datetime
import csv
import socket
from netmiko import ConnectHandler
from netmiko.ssh_exception import NetMikoTimeoutException,NetMikoAuthenticationException
import time
import ipaddress
import logging
logging.raiseExceptions=False

def validate_ipaddress(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError as errorCode:
        #uncomment below if you want to display the exception message.
        #print(errorCode)
        #comment below if above is uncommented.
        pass
        return False

def check_ping(hostname):

    # just do a quick ping test to the remote server
    # there's no point going further if we can't ping it
    output = subprocess.Popen(["ping.exe",hostname],stdout = subprocess.PIPE).communicate()[0]

    if ('unreachable' in output):
        return False
    else:
        return True

def consistDetector(sourceAddr):
    
    switch = {
        'device_type': 'cisco_ios',
        'ip': sourceAddr,
        'username': 'cisco',
        'password': 'cisco',
        'secret': 'cisco',
        'port' : 22,          # optional, defaults to 22
        'verbose': False,       # optional, defaults to False
        'global_delay_factor': 4 # for remote systems when the network is slow
    }
    try:

        
        # the minimum packet size is 36
        # so if someone puts in a smaller value we assume they mean "smallest possible"
            
        # this is what we connect to
        net_connect = ConnectHandler(**switch)
        print "We're in " + sourceAddr
        print sourceAddr
        
        ospf77 = u""
        ospf88 = u""
        # we get the ospf neighbors
        # and parse out the IPs for forward and reverse neighbors
        time.sleep(1)
        ospfCommand = "show ospf neighbor vlan " + str(77)
        ospf77 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]
        try:
            if validate_ipaddress(ospf77):
                print "We got OSPF 77"
            else: 
                ospf77 = ""
        except UnboundLocalError:
            ospf77 = ""
        time.sleep(1)
        ospfCommand = "show ospf neighbor vlan " + str(88)
        ospf88 = net_connect.send_command(ospfCommand).split('\n')[-1].split(' ')[0]
        try:
            if validate_ipaddress(ospf88):
                print "We got OSPF 88"
            else: 
                ospf88 = ""
        except UnboundLocalError:
            ospf88 = ""
            
        # we always sanely disconnect
        net_connect.disconnect()
        print "Disconnected from " + sourceAddr
        # we use this as row data in the output
        currentTime = str(datetime.time(datetime.now()))
        
        for assetNum in consistAll:
            if sourceAddr in consistAll[assetNum]['SW0']:
                localAsset = str(assetNum)
                break
            elif sourceAddr in consistAll[assetNum]['SW1']:
                localAsset = str(assetNum)
                break
        
        consistActual[localAsset] = {}
        consistActual[localAsset]['IP'] = sourceAddr
        
        global sourceAsset
        
        beenHere77 = False
        # if there's no ospf peer we just skip this
        if ospf77:
            for assetNum in consistAll:
                if ospf77 == consistAll[assetNum]['SW0']:
                    ospf77Asset = str(assetNum)
                    break
                elif ospf77 == consistAll[assetNum]['SW1']:
                    ospf77Asset = str(assetNum)
                    break
            for assetNum in consistActual:
                if ospf77Asset == assetNum:
                    beenHere77 = True
                    break
            if not beenHere77:
                consistActual[localAsset]['Vl77'] = ospf77Asset
        else:
            ospf77Asset = ""
        
        beenHere88 = False        
        # if there's no ospf peer we just skip the ping test
        if ospf88:
            
            for assetNum in consistAll:
                if ospf88 == consistAll[assetNum]['SW0']:
                    ospf88Asset = str(assetNum)
                    break
                elif ospf88 == consistAll[assetNum]['SW1']:
                    ospf88Asset = str(assetNum)
                    break
            for assetNum in consistActual:
                if ospf88Asset == assetNum:
                    beenHere88 = True
                    break
            if not beenHere88:
                consistActual[localAsset]['Vl88'] = ospf88Asset
        else:
            ospf88Asset = ""
            
        # append to master CSV        
        # this creates a single CSV for this host for all tests
        global sourceAsset
        with open(sourceAsset + ".csv", "ab") as csvfile:
            csvoutput = csv.writer(csvfile, delimiter=',')
            # iterate through the dictionary and
            # drop the value, key pairs as variables that we can reference
            # peerIP is IP of the neighbor (for either vlan 77 or 88)
            # dictLoop is a dictionary containing the results of the tests
            csvoutput.writerow([localAsset,sourceAddr,ospf77Asset,ospf88Asset])
        # sanely close the file handler
        csvfile.close()
        print "Written to CSV"
        
        if not beenHere77:
            time.sleep(1)
            consistDetector(ospf77)
        if not beenHere88:
            time.sleep(1)
            consistDetector(ospf88)

    except NetMikoTimeoutException,NetMikoAuthenticationException:
        return

# these are the systems we're going to test
consistBrainFile = csv.DictReader(open("consistBrainList.csv"))

# initialize the test dictionary
consistBrains = {}

# run through the CSV and push the test setup into the test dictionary
for row in consistBrainFile:
    consistBrains[row['sourceAsset']] = {}
    consistBrains[row['sourceAsset']]['SW0'] = row['SW0']
    consistBrains[row['sourceAsset']]['SW1'] = row['SW1']

# this is the consist switch layout
# we use it to figure out what assets our peers are part of
consistFile = csv.DictReader(open("consistList.csv"))

# initialize the consist dictionary
consistAll = {}

# run through the CSV and push the consist data into the dictionary
for row in consistFile:
    consistAll[row['sourceAsset']] = {}
    consistAll[row['sourceAsset']]['SW0'] = row['SW0']
    consistAll[row['sourceAsset']]['SW1'] = row['SW1']

# we use this as the CSV filename for output
currentDateTime = str((datetime.date(datetime.now())))

consistActual = {}

global sourceAsset

for asset, assetData in sorted(consistBrains.items()):
    # we make sure we can ping the switch before we do anything else
    sourceAsset = asset
    if check_ping(assetData['SW0']):
        print "We can ping " + assetData['SW0']
        consistDetector(assetData['SW0'])
    else:
        print "We cannot ping " + assetData['SW0']