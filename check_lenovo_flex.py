#!/usr/bin/python
#
# Copyright 2010, Pall Sigurdsson <palli@opensource.is>
#
# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This script is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# About this script
# 
# This script will check the status of a remote Lenovo Enterprise Flex Chassis
# orginal file check_ibm_bladecenter.py renamed and modified by Silvio Erdenberger, 
#
# version 1.3
# 8.12.2017
# adding
# * add coolingzone feature 
#
# fixes
# * fix wrong compares in fans (fans)
#
# changes
# * rewrite the check_fans
#
#
# version 1.2
# 30.11.2017
# changes 
# * renamed --snmp-password to --snmp_apassword
# * fix a wrong validation of Authentication password in the options parameter
# * fix some typo in the help
# 
# version 1.1
# 17.11.2017
# change filename to check_lenovo_flex.py
# there are several changes to the IBM Bladecenter, whic are not compatible
# changes in version 1.1
# * add possibility to a Privacy Password for authPriv in snmp_security_level
# * required parameter depending on --snmp_security_level
# * add authentication encryption and password
# * add privacy encryption and password
#
# powermodules
#
# system-health -> adjust to flex chassis
#  if no error, the error oid don't exist
#
# temperature -> no change
#
# chassis-status to flex adjusted 
#
# bladehealth
#
# fans -> adjust to flex chassis
#
# coolingzones 
# implemented on fan based devices
# TODO change the OID ChassisCoolingZone
# but some issues appear
#  
# switchmodules
#  


# No real need to change anything below here
version="1.3"
ok=0
warning=1
critical=2
unknown=3 
not_present = -1 
exit_status = -1

state = {}
state[not_present] = "Not Present"
state[ok] = "OK"
state[warning] = "Warning"
state[critical] = "Critical"
state[unknown] = "Unknown"

longserviceoutput="\n"
perfdata=""
summary=""
sudo=False

from sys import exit
from sys import argv
from os import getenv,putenv,environ
import subprocess


# Parse some Arguments
from optparse import OptionParser
parser = OptionParser()
parser.add_option("-m","--mode", dest="mode",
	help="Which check mode is in use (powermodules,system-health,temperature,chassis-status,bladehealth,fans,switchmodules,coolingzones)")
parser.add_option("-H","--host", dest="host",
	help="Hostname or IP address of the host to check")
parser.add_option("-w","--warning", dest="warning_threshold",
	help="Warning threshold", type="int", default=None)
parser.add_option("-c","--critical", type="int", dest="critical_threshold",
	help="Critical threshold", default=None)
parser.add_option("-e","--exclude", dest="exclude",
	help="Exclude specific object", default=None)
parser.add_option("-v","--snmp_version", dest="snmp_version",
	help="SNMP Version to use (1, 2c or 3)", default="1")
parser.add_option("-u","--snmp_username", dest="snmp_username",
	help="SNMP username (only with SNMP v3)", default=None)
parser.add_option("-C","--snmp_community", dest="snmp_community",
	help="SNMP Community (only with SNMP v1|v2c)", default=None)
parser.add_option("-p","--snmp_apassword", dest="snmp_apassword",
	help="SNMP authentication password (only with SNMP v3)", default=None)
parser.add_option("-a","--snmp_aprotocol", dest="snmp_aprotocol",
	help="SNMP authentication protocol (SHA only with SNMP v3)", default=None)
parser.add_option("-x","--snmp_ppassword", dest="snmp_ppassword",
	help="SNMP privacy password (only with SNMP v3)", default=None)
parser.add_option("-X","--snmp_pprotocol", dest="snmp_pprotocol",
	help="SNMP privacy protocol AES||DES (only with SNMP v3)", default=None)
parser.add_option("-l","--snmp_security_level", dest="snmp_seclevel",
	help="SNMP security level (only with SNMP v3) (noAuthNoPriv|authNoPriv|authPriv)", default=None)
parser.add_option("-t","--snmp_timeout", dest="snmp_timeout",
	help="Timeout in seconds for SNMP", default=10)
parser.add_option("-d","--debug", dest="debug",
	help="Enable debugging (for troubleshooting", action="store_true", default=False)

(opts,args) = parser.parse_args()


if opts.host == None:
	parser.error("Hostname (-H) is required.")
if opts.mode == None:
	parser.error("Mode (--mode) is required.")

snmp_options = ""
def set_snmp_options():
	global snmp_options
	if opts.snmp_version is not None:
		snmp_options = snmp_options + " -v%s" % opts.snmp_version
	if opts.snmp_version == "3":
		if opts.snmp_username is None:
			parser.error("--snmp_username required with --snmp_version=3")
		if opts.snmp_seclevel is None:
			parser.error("--snmp_security_level required with --snmp_version=3")
		if opts.snmp_seclevel == "noAuthNoPriv":
			snmp_options = snmp_options + " -l %s -u %s " % (opts.snmp_seclevel,opts.snmp_username)
		if opts.snmp_seclevel == "authNoPriv":
			if opts.snmp_apassword is None:
				parser.error("--snmp_apassword required with --snmp_version=3")
			if opts.snmp_aprotocol is None:
				parser.error("--snmp_aprotocol required with --snmp_version=3")
			snmp_options = snmp_options + " -l %s -u %s -a %s -A %s " % (opts.snmp_seclevel,opts.snmp_username,opts.snmp_aprotocol,opts.snmp_apassword)
		if opts.snmp_seclevel == "authPriv":
			if opts.snmp_pprotocol is None:
				parser.error("--snmp_pprotocol required with --snmp_version=3")
			if opts.snmp_ppassword is None:
				parser.error("--snmp_ppassword required with --snmp_version=3")
			if opts.snmp_apassword is None:
				parser.error("--snmp_apassword required with --snmp_version=3")
			if opts.snmp_aprotocol is None:
				parser.error("--snmp_aprotocol required with --snmp_version=3")
			snmp_options = snmp_options + " -l %s -u %s -a %s -A %s -x %s -X %s " % (opts.snmp_seclevel,opts.snmp_username,opts.snmp_aprotocol,opts.snmp_apassword,opts.snmp_pprotocol,opts.snmp_ppassword)
	else:
		if opts.snmp_community is None:
			parser.error("--snmp_community is required with --snmp_version=1|2c")
		snmp_options = snmp_options + " -c %s " % opts.snmp_community 
	snmp_options += " -t %s " % (opts.snmp_timeout)

def error(errortext):
        print "* Error: %s" % errortext
        exit(unknown)

def debug( debugtext ):
        if opts.debug:
                print  debugtext

def nagios_status( newStatus ):
	global exit_status
	exit_status = max(exit_status, newStatus)
	return exit_status

'''runCommand: Runs command from the shell prompt. Exit Nagios style if unsuccessful'''
def runCommand(command):
  debug( "Executing: %s" % command )
  proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE,)
  stdout, stderr = proc.communicate('through stdin to stdout')
  if proc.returncode > 0:
    print "Error %s: %s\n command was: '%s'" % (proc.returncode,stderr.strip(),command)
    debug("results: %s" % (stdout.strip() ) )
    if proc.returncode == 127: # File not found, lets print path
        path=getenv("PATH")
        print "Check if your path is correct %s" % (path)
    if stderr.find('Password:') == 0 and command.find('sudo') == 0:
      print "Check if user is in the sudoers file"
    if stderr.find('sorry, you must have a tty to run sudo') == 0 and command.find('sudo') == 0:
      print "Please remove 'requiretty' from /etc/sudoers"
    exit(unknown)
  else:
    return stdout

def end():
	global summary
	global longserviceoutput
	global perfdata
	global exit_status
        print "%s - %s | %s" % (state[exit_status], summary,perfdata)
        print longserviceoutput
	if exit_status < 0: exit_status = unknown
        exit(exit_status)

def add_perfdata(text):
        global perfdata
        text = text.strip()
        perfdata = perfdata + " %s " % (text)

def add_long(text):
        global longserviceoutput
        longserviceoutput = longserviceoutput + text + '\n'

def add_summary(text):
	global summary
	summary = summary + text

def set_path(path):
	current_path = getenv('PATH')
	if current_path.find('C:\\') > -1: # We are on this platform
		if path == '':
			pass
		else: path = ';' + path
	else:	# Unix/Linux, etc
		if path == '': path = ":/usr/sbin"
		else: path = ':' + path
	current_path = "%s%s" % (current_path,path)
	environ['PATH'] = current_path



def snmpget(oid):
	snmpgetcommand = "snmpget %s %s %s" % (snmp_options,opts.host,oid)
	output = runCommand(snmpgetcommand)
	oid,result = output.strip().split(' = ', 1)
	resultType,resultValue = result.split(': ',1)
	if resultType == 'STRING': # strip quotes of the string
		resultValue = resultValue[1:-1]
	return resultValue

# snmpwalk -v3 -u v3get mgmt-rek-proxy-p02 -A proxy2011 -l authNoPriv 1.3.6.1.4.1.15497
def snmpwalk(base_oid):
	snmpwalkcommand = "snmpwalk %s %s %s" % (snmp_options, opts.host, base_oid)
	output = runCommand(snmpwalkcommand + " " + base_oid)
	return output

def getTable(base_oid):
	myTable = {}
	output = snmpwalk(base_oid)
	for line in output.split('\n'):
		tmp = line.strip().split(' = ', 1)
		if len(tmp) == 2:
			oid,result = tmp
		else:
			result = result + tmp[0]
#			continue
		tmp = result.split(': ',1)
		if len(tmp) > 1:
			resultType,resultValue = tmp[0],tmp[1]
		else:
			resultType = None
			resultValue = tmp[0]
		if resultType == 'STRING': # strip quotes of the string
			resultValue = resultValue[1:-1]
		index = oid.strip().split('.')
		column = int(index.pop())
		row = int(index.pop())
		if not myTable.has_key(column): myTable[column] = {}
		myTable[column][row] = resultValue
	return myTable

def check_powermodules():
                                 #BASE OID
				 #               #SUPPORT PROCESSOR
                                 #               #  #CMM OID
				 #               #  # #MONITORS
                                 #               #  # # #POWER MOD
	powermodules = getTable('1.3.6.1.4.1.2.3.51.2.2.4')
	index,exists,status,details = (1,2,3,4)
	num_ok = 0
	for i in powermodules.values():
		myIndex = i[index]
		myStatus = i[status]
		myDetails = i[details]
		myExists = i[exists]
		if myIndex == opts.exclude: continue
		if myStatus != "1":
			nagios_status(warning)
			add_summary( 'Powermodule "%s" status "%s". %s. ' % (myIndex,myStatus,myDetails) )
		else:
			num_ok = num_ok + 1
		add_long('Powersupply "%s" status "%s". %s. ' % (myIndex,myStatus,myDetails) )
	add_summary( "%s out of %s powermodules are healthy" % (num_ok, len(powermodules) ) )
	add_perfdata( "'Number of powermodules'=%s" % (len(powermodules) ) )
			
	nagios_status(ok)

def check_switchmodules():
                                  #BASE OID
                                  #                  #CMM
				  #                  #  #COMPONENTS
                                  #                  #  #     #SWITCH OID
	switchmodules = getTable("1.3.6.1.4.1.2.3.51.2.22.3.1.1")
	# The following oid is undocumented, but contains some useful extra info
	try:
		extrainfo = getTable("1.3.6.1.4.1.2.3.51.2.22.3.1.7").values()
	except:
		extrainfo = []
	for module in switchmodules.values():
		myIndex = module[1]
		healthstate = module[15]
		resultavailable = module[3]
		resultvalue = module[4]
		enabledisable = module[6]
		if resultavailable == "1":
			'this module is installed'
			if healthstate == "1":
				nagios_status(ok)
				add_long("Module%s health good.\n  post=%s" % (myIndex,resultvalue))
			else:
				nagios_status(warning)
				add_long("Module%s health bad(%s).\n  post=%s" % (myIndex, healthstate,resultvalue) )
				add_summary("Problem with Module %s. " % (myIndex))
			if len(extrainfo) > int(myIndex):
				myExtraInfo = extrainfo[int(myIndex)-1]
				module_type = myExtraInfo[22]
				module_ip = myExtraInfo[6]
				add_long( "  type=%s ip=%s" % (module_type,module_ip) )
	if exit_status == ok:
		add_summary("All switchmodules healthy")
		

def check_fans():
	" Check fan status "
                         #BASE OID
                         #           #CMM OID
                         #           #            #FAN OID
	fans = getTable("1.3.6.1.4.1.2.3.51.2.2.3.50")
	chassisFanIndex,chassisFanId,chassisFanSpeed,chassisFanState,chassisFanSpeedRPM,chassisFanControllerState,chassisFanCoolingZone = (1,2,3,4,5,6,7)
	for i in fans.values():
		debug("i %s" % i)
		mychassisFanSpeedRPM = i[chassisFanSpeedRPM] 
		mychassisFanSpeedRPM = mychassisFanSpeedRPM.split(None,1)[0]
		debug("mychassisFanSpeedRPM %s" % mychassisFanSpeedRPM)
		if i[chassisFanControllerState] != "2": # not notPresent -> present
			add_long( "Fan %s state=%s speed=%s" % (i[chassisFanIndex],i[chassisFanState],i[chassisFanSpeedRPM]) )
			add_perfdata("Fan%s=%s" %(i[chassisFanIndex],mychassisFanSpeedRPM ))
			# Check fan i
			if i[chassisFanState] == "1":
				nagios_status(ok)
			else:
				add_summary("Fan%s NOT OK. " % i[chassisFanIndex])
				nagios_status(warning)

#	num_ok = 0
#	for i in range(1,4):
#		if fans[i][chassisFanState] != "1":
#			num_ok = num_ok + 1
#	if num_ok > 1:
#		add_summary("ChassisCoolingZone1 NOT OK. ")
#		nagios_status(critical)
#	num_ok = 0
#	for i in range(6,9):
#		if fans[i][chassisFanState] != "1":
#			num_ok = num_ok + 1
#	if num_ok > 1:
#		add_summary("ChassisCoolingZone2 NOT OK. ")
#		nagios_status(critical)
#	if fans[5][chassisFanState] != "1" or fans[10][chassisFanState] != "1":
#		add_summary("ChassisCoolingZone 3 and 4 NOT OK. ")
#		nagios_status(critical)

def check_coolingzones():
	" Check cooling zone status "
                         #BASE OID
                         #           #CMM OID
                         #           #            #FAN OID
	fans = getTable("1.3.6.1.4.1.2.3.51.2.2.3.50")
	chassisFanIndex,chassisFanId,chassisFanSpeed,chassisFanState,chassisFanSpeedRPM,chassisFanControllerState,chassisFanCoolingZone = (1,2,3,4,5,6,7)
#	for i in fans.values():
#		debug("i %s" % i)
#		mychassisFanSpeedRPM = i[chassisFanSpeedRPM] 
#		mychassisFanSpeedRPM = mychassisFanSpeedRPM.split(None,1)[0]
#		debug("mychassisFanSpeedRPM %s" % mychassisFanSpeedRPM)
#		if i[chassisFanControllerState] != "2": # not notPresent -> present
#			add_long( "Fan %s state=%s speed=%s" % (i[chassisFanIndex],i[chassisFanState],i[chassisFanSpeedRPM]) )
#			add_perfdata("Fan%s=%s" %(i[chassisFanIndex],mychassisFanSpeedRPM ))
#			# Check fan i
#			if i[chassisFanState] == "1":
#				nagios_status(ok)
#			else:
#				add_summary("Fan%s NOT OK. " % i[chassisFanIndex])
#				nagios_status(warning)
#
	num_ok = 0
	for i in range(1,4):
		if fans[i][chassisFanState] == "2" or fans[i][chassisFanState] == "3":
			num_ok = num_ok + 1
	if num_ok == 0:
		add_summary("ChassisCoolingZone1 OK. ")
		nagios_status(ok)
	elif num_ok == 1:
		add_summary("ChassisCoolingZone1 NOT OK. ")
		nagios_status(warning)
	else:
		add_summary("ChassisCoolingZone1 NOT OK. ")
		nagios_status(critical)
		
	num_ok = 0
	for i in range(6,9):
		if fans[i][chassisFanState] == "2" or fans[i][chassisFanState] == "3":
			num_ok = num_ok + 1
	if num_ok == 0:
		add_summary("ChassisCoolingZone2 OK. ")
		nagios_status(ok)
	elif num_ok == 1:
		add_summary("ChassisCoolingZone2 NOT OK. ")
		nagios_status(warning)
	else:
		add_summary("ChassisCoolingZone2 NOT OK. ")
		nagios_status(critical)

	if fans[5][chassisFanState] != "1":
		add_summary("ChassisCoolingZone 3 NOT OK. ")
		nagios_status(critical)
	else:
		add_summary("ChassisCoolingZone 3 OK. ")
		nagios_status(ok)

	if fans[10][chassisFanState] != "1":
		add_summary("ChassisCoolingZone 4 NOT OK. ")
		nagios_status(critical)
	else:
		add_summary("ChassisCoolingZone 4 OK. ")
		nagios_status(ok)
		

#######TODO STUFF#############
#                                       #BASE OID
#                                       #           #CMM OID
#                                       #           #            #COOLINGZONE OID
#	ChassisCoolingZone = getTable("1.3.6.1.4.1.2.3.51.2.2.3.51")
#	chassisCoolingIndex,chassisCoolingZone,chassisCoolingZoneStatus,chassisCoolingZoneComponent = (1,2,3,4)
#	nok_zone1 = 0
#	nok_zone2 = 0
#	for i in ChassisCoolingZone.values():
#		debug("i %s" % i)
#		if i[chassisCoolingZoneStatus] == "0" or i[chassisCoolingZoneStatus] == "1":
#			continue
#		elif i[chassisCoolingZoneStatus] == "2":
#			if i[chassisCoolingZone] == 1:
#				nok_zone1 = nok_zone1 + 1
#			elif i[chassisCoolingZone] == 2:
#				nok_zone2 = nok_zone2 + 1
#		elif i[chassisCoolingZoneStatus] == "3":
#			if i[chassisCoolingZone] == 1:
#				nok_zone1 = nok_zone1 + 2
#			elif i[chassisCoolingZone] == 2:
#				nok_zone2 = nok_zone2 + 2
#	
#	add_long( "ChassisCoolingZone %s state=%s " % (i[chassisCoolingZone],i[chassisCoolingZoneStatus]))
#	add_summary("ChassisCoolingZone%s OK. " % i[chassisCoolingZoneStatus])
#	nagios_status(ok)
#
#
#	add_summary("ChassisCoolingZone%s NOT OK. " % i[chassisCoolingZoneStatus])
#	nagios_status(warning)
#
#
#	add_summary("ChassisCoolingZone%s NOT OK. " % i[chassisCoolingZoneStatus])
#	nagios_status(critical)


def check_chassis_status():
	chassis = getTable('1.3.6.1.4.1.2.3.51.2.2.5.2')
	oids = chassis.values()[0]
	chassis_oid = {
		10 :"bistBootRomFlashImage",
		11 :"bistEthernetPort1",
		113 :"bistSwitchModulesCommunicating",
		14 :"bistExternalI2CDevices",
		19 :"bistInternalEthernetSwitch",
		25 :"bistPrimaryKernel",
		26 :"bistSecondaryKernel",
		29 :"bistPhysicalNetworkLink",
		30 :"bistLogicalNetworkLink",
		33 :"bistBladesInstalled",
		49 :"bistBladesCommunicating",
		5  :"bistRtc",
		65 :"bistBlowersInstalled",
		7  :"bistLocalI2CBus",
		73 :"bistBlowersFunctional",
		74 :"bistMediaTrayInstalled",
		75 :"bistMediaTrayCommunicating",
		8  :"bistPrimaryMainAppFlashImage",
		81 :"bistPowerModulesInstalled",
		89 :"bistPowerModulesFunctional",
		9  :"bistSecondaryMainAppFlashImage",
		97 :"bistSwitchModulesInstalled",
	}
	
	# Check if all blades are working
	bistBladesInstalled = 33
	bistBlowersInstalled = 65
	bistMediaTrayInstalled = 74
	bistPowerModulesInstalled = 81
	bistSwitchModulesInstalled = 97
	bistSwitchModulesCommunicating = 113
	bistBladesCommunicating = 49
	bistMediaTrayCommunicating = 75
	bistBlowersFunctional = 73
	bistPowerModulesFunctional = 89
	
	# Check Blade Communications
	if not oids.has_key(bistBladesInstalled) or not oids.has_key(bistBladesCommunicating):
		add_summary( "Blades N/A. ")
	elif oids[bistBladesInstalled] == oids[bistBladesCommunicating]:
		nagios_status(ok)
		add_summary( "Blades OK. " )
	else:
		nagios_status(warning)
		add_summary( "Blades NOT OK. " )
	# Check PowerModule Status
	if not oids.has_key(bistPowerModulesFunctional) or not oids.has_key(bistPowerModulesInstalled):
		add_summary( "Powermodules N/A. ")
	elif oids[bistPowerModulesFunctional] == oids[bistPowerModulesInstalled]:
		nagios_status(ok)
		add_summary( "PowerModules OK. " )
	else:
		nagios_status(warning)
		add_summary( "PowerModules NOT OK. " )
	
	# Check SwitchModule Communications
	if not oids.has_key(bistSwitchModulesCommunicating) or not oids.has_key(bistSwitchModulesInstalled):
		add_summary( "SwitchModules N/A. ")
	if oids[bistSwitchModulesCommunicating] == oids[bistSwitchModulesInstalled]:
		nagios_status(ok)
		add_summary("Switchmodules OK. ")
	else:
		nagios_status(warning)
		add_summary( "Switchmodules NOT OK. ")
	# Check fan status
	if not oids.has_key(bistBlowersInstalled) or not oids.has_key(bistBlowersFunctional):
		add_summary( "Blowers N/A. ")
	elif oids[bistBlowersInstalled] == oids[bistBlowersFunctional]:
		nagios_status(ok)
		add_summary( "Blowers OK. " )
	else:
		nagios_status(warning)
		add_summary( "Blowers NOT OK. " )
	# Check Media Tray Status
	if not oids.has_key(bistMediaTrayCommunicating) or not oids.has_key(bistMediaTrayInstalled):
		nagios_status(ok)
		add_summary( "Media Trays N/A. ")
	elif oids[bistMediaTrayCommunicating] == oids[bistMediaTrayInstalled]:
		add_summary( "Media Trays OK. " )
	else:
		nagios_status(warning)
		add_summary( "Media Trays NOT OK. " )
	
	
	# status_oids, oids that where 0 == ok
	status_oids = ( 5,7,8,9,10,11,14,19,20,21,22,23,24,25,26,27,28,29,30, )
	
	add_long("Other Sensors: ")
	sensor_status = ok	
	for oid in status_oids:
		if not chassis_oid.has_key(oid): continue
		oidValue = oids[oid]
		oidName = chassis_oid[oid]
		if oidValue == "0":
			friendly_status = "%s (ok)" % oidValue
		else:
			friendly_status = "%s (not ok)" % oidValue
			nagios_status(warning)
			sensor_status = warning
			add_summary( "%s is %s" % oidName, friendly_status)
		add_long( " %s status: %s" % (oidName,friendly_status) )
	if sensor_status == ok:
		add_summary( "Other Sensors: OK. ")
			

def check_bladehealth():
	blades = getTable('1.3.6.1.4.1.2.3.51.2.22.1.5.2.1')
	bladestate = getTable('1.3.6.1.4.1.2.3.51.2.22.1.5.1.1').values()
	index,bladeid,severity,description = (1,2,3,4)
	good_blades = 0
	total_blades = 0
	for i,row in enumerate(blades.values()):
		myIndex = row[index]
		myBladeid = row[bladeid]
		mySeverity = row[severity]
		myDescription = row[description]
		try: myName = bladestate[i][6]
		except: myName = ""
		if mySeverity == "(No severity)": continue
		add_long( "blade%s (%s): %s %s" % (myBladeid,myName,mySeverity, myDescription) )
		total_blades += 1
		if mySeverity == 'Good':
			nagios_status(ok)
			good_blades += 1
		else:
			nagios_status(warning)
			add_summary( "blade%s (%s): %s %s. " % (myBladeid,myName,mySeverity, myDescription) )
	if good_blades == total_blades:
		add_summary( "%s out of %s blades in Good health. " % (good_blades, total_blades))
		nagios_status(ok)
	else:
		nagios_status(warning)

def check_systemhealth():
	systemhealthstat = snmpget('1.3.6.1.4.1.2.3.51.2.2.7.1.0')
	index,severity,description,date = (1,2,3,4)
	# Check overall health
	if systemhealthstat == '255':
		nagios_status(ok)
		add_summary("Bladecenter health: OK. ")
	elif systemhealthstat == "2":
		nagios_status(warning)
		add_summary("Non-Critical Error. ")
	elif systemhealthstat == "4":
		nagios_status(critical)
		add_summary("System-Level Error. ")
	elif systemhealthstat == "0":
		nagios_status(critical)
		add_summary("Critical. ")
	else:
		nagios_status(unknown)
		add_summary("Bladecenter health unkown (oid 1.3.6.1.4.1.2.3.51.2.2.7.1.0 returns %s). " % systemhealthstat)
	if systemhealthstat == "2" or systemhealthstat == "4" or systemhealthstat == "0": 
		summary = getTable('1.3.6.1.4.1.2.3.51.2.2.7.2.1')
		for row in summary.values():
			if row[severity] == 'Good':
				nagios_status(ok)
			elif row[severity] == 'Warning':
				nagios_status(warning)
			else:
				nagios_status(critical)
			text_row_description = row[description]
			text_row_description = text_row_description.replace(" ", "")
			text_row_description = text_row_description.decode("hex")
			add_summary( "%s. " % (text_row_description) )
			add_long( "* %s. " % (text_row_description) )
	
def check_temperature():
	# set some sensible defaults
	if opts.warning_threshold is None: opts.warning_threshold = 28
	if opts.critical_threshold is None: opts.critical_threshold = 35
	str_temp = snmpget('1.3.6.1.4.1.2.3.51.2.2.1.5.1.0')
	float_temp,measurement = str_temp.split(None, 1)
	float_temp = float( float_temp )
	if opts.critical_threshold is not None and float_temp > opts.critical_threshold:
		nagios_status(critical)
		add_summary( "ambient temperature (%s) is over critical thresholds (%s). " % (str_temp, opts.critical_threshold) )
	elif opts.warning_threshold is not None and float_temp > opts.warning_threshold:
		nagios_status(warning)
		add_summary( "ambient temperature (%s) is over warning thresholds (%s). " % (str_temp, opts.warning_threshold) )
	else:
		add_summary( "Ambient temperature = %s. " % (str_temp) )
	add_perfdata( "'ambient_temp'=%s;%s;%s " % (float_temp,opts.warning_threshold,opts.critical_threshold) )
	#add_long( "Ambient Temperature = %s" % (str_temp) )
	nagios_status(ok)
	


if __name__ == '__main__':
	try:
		set_snmp_options()
		if opts.mode == 'powermodules':
			check_powermodules()
		elif opts.mode == 'system-health':
			check_systemhealth()
		elif opts.mode == 'temperature':
			check_temperature()
		elif opts.mode == 'chassis-status':
			check_chassis_status()
		elif opts.mode == 'bladehealth':
			check_bladehealth()
		elif opts.mode == 'fans':
			check_fans()
		elif opts.mode == 'coolingzones':
			check_coolingzones()
		elif opts.mode == 'switchmodules':
			check_switchmodules()
		else:
			parser.error("%s is not a valid option for --mode" % opts.mode)
	except Exception, e:
		print "Unhandled exception while running script: %s" % e
		exit(unknown)
	end()

