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
# serdenberger@lenovo.com 17.11.2017
# change filename to check_lenovo_flex.py
# there are several changes to the IBM Bladecenter, whic are not compatible
# changes in version 1.1
# * add possibility to a Privacy Password for authPriv in snmp_security_level
# * equired paramater depending on --snmp_security_level
# * add 
# *
# *
# *
# *
#
# powermodules
#
# system-health -> adjust to flex chassis
#  if no error, the error oid don't exist
#  
#
# temperature -> no change
#
# chassis-status to flex adjusted 
#
# bladehealth
#
# blowers -> expand the blowers to 10 (fans)
#  
#
# switchmodules
#  


# No real need to change anything below here
version="1.1"
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
	help="Which check mode is in use (powermodules,system-health,temperature,chassis-status,bladehealth,blowers,switchmodules)")
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
parser.add_option("-p","--snmp_password", dest="snmp_password",
	help="SNMP password (only with SNMP v3)", default=None)
parser.add_option("-a","--snmp_aprotocol", dest="snmp_aprotocol",
	help="SNMP authenthication protocol SHA (only with SNMP v3)", default=None)
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
		if opts.snmp_password is None:
			parser.error("--snmp_password required with --snmp_version=3")
		if opts.snmp_seclevel == "noAuthNoPriv":
			snmp_options = snmp_options + " -l %s -u %s " % (opts.snmp_seclevel,opts.snmp_username)
		if opts.snmp_seclevel == "authNoPriv":
			if opts.snmp_aprotocol is None:
				parser.error("--snmp_aprotocol required with --snmp_version=3")
			snmp_options = snmp_options + " -l %s -u %s -a %s -A %s " % (opts.snmp_seclevel,opts.snmp_username,opts.snmp_aprotocol,opts.snmp_password)
		if opts.snmp_seclevel == "authPriv":
			if opts.snmp_pprotocol is None:
				parser.error("--snmp_pprotocol required with --snmp_version=3")
			if opts.snmp_ppassword is None:
				parser.error("--snmp_ppassword required with --snmp_version=3")
			if opts.snmp_aprotocol is None:
				parser.error("--snmp_aprotocol required with --snmp_version=3")
			snmp_options = snmp_options + " -l %s -u %s -a %s -A %s -x %s -X %s " % (opts.snmp_seclevel,opts.snmp_username,opts.snmp_aprotocol,opts.snmp_password,opts.snmp_pprotocol,opts.snmp_ppassword)
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
	powermodules = getTable('1.3.6.1.4.1.2.3.51.2.2.4')
	index = 1
	exists = 2
	status = 3
	details = 4
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
		

def check_blowers():
	" Check blower status "
	blowers = getTable("1.3.6.1.4.1.2.3.51.2.2.3.50")

	# This mib only seems to support 10 blowers. 
	blower1speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.1")
	blower1state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.1")
	
	blower2speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.2")
	blower2state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.2")
	
	blower3speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.3")
	blower3state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.3")
	
	blower4speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.4")
	blower4state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.4")
	
	blower5speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.5")
	blower5state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.5")
	
	blower6speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.6")
	blower6state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.6")
	
	blower7speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.7")
	blower7state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.7")
	
	blower8speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.8")
	blower8state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.8")
	
	blower9speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.9")
	blower9state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.9")
	
	blower10speed = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.5.10")
	blower10state = snmpget("1.3.6.1.4.1.2.3.51.2.2.3.50.1.4.10")
	
	add_long( "Blower 1 state=%s speed=%s" % (blower1state,blower1speed) )
	add_long( "Blower 2 state=%s speed=%s" % (blower2state,blower2speed) )
	add_long( "Blower 3 state=%s speed=%s" % (blower3state,blower3speed) )
	add_long( "Blower 4 state=%s speed=%s" % (blower4state,blower4speed) )
	add_long( "Blower 5 state=%s speed=%s" % (blower5state,blower5speed) )
	add_long( "Blower 6 state=%s speed=%s" % (blower6state,blower6speed) )
	add_long( "Blower 7 state=%s speed=%s" % (blower7state,blower7speed) )
	add_long( "Blower 8 state=%s speed=%s" % (blower8state,blower8speed) )
	add_long( "Blower 8 state=%s speed=%s" % (blower9state,blower9speed) )
	add_long( "Blower 10 state=%s speed=%s" % (blower10state,blower10speed) )
	add_perfdata("blower1=%s" %(blower1speed.split(None,1)[0] ))
	add_perfdata("blower2=%s" %(blower2speed.split(None,1)[0] ))
	add_perfdata("blower3=%s" %(blower3speed.split(None,1)[0] ))
	add_perfdata("blower4=%s" %(blower4speed.split(None,1)[0] ))
	add_perfdata("blower5=%s" %(blower5speed.split(None,1)[0] ))
	add_perfdata("blower6=%s" %(blower6speed.split(None,1)[0] ))
	add_perfdata("blower7=%s" %(blower7speed.split(None,1)[0] ))
	add_perfdata("blower8=%s" %(blower8speed.split(None,1)[0] ))
	add_perfdata("blower9=%s" %(blower9speed.split(None,1)[0] ))
	add_perfdata("blower10=%s" %(blower10speed.split(None,1)[0] ))
	# Check blower 1
	if blower1state == "1":
		nagios_status(ok)
		add_summary("Blower1 OK. " )
	else:
		add_summary("Blower1 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 2
	if blower2state == "1":
		nagios_status(ok)
		add_summary("Blower2 OK. " )
	else:
		add_summary("Blower2 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 3
	if blower3state == "1":
		nagios_status(ok)
		add_summary("Blower3 OK. " )
	else:
		add_summary("Blower3 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 4
	if blower4state == "1":
		nagios_status(ok)
		add_summary("Blower4 OK. " )
	else:
		add_summary("Blower4 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 5
	if blower5state == "1":
		nagios_status(ok)
		add_summary("Blower5 OK. " )
	else:
		add_summary("Blower5 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 6
	if blower6state == "1":
		nagios_status(ok)
		add_summary("Blower6 OK. " )
	else:
		add_summary("Blower6 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 7
	if blower7state == "1":
		nagios_status(ok)
		add_summary("Blower7 OK. " )
	else:
		add_summary("Blower7 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 8
	if blower8state == "1":
		nagios_status(ok)
		add_summary("Blower8 OK. " )
	else:
		add_summary("Blower8 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 9
	if blower9state == "1":
		nagios_status(ok)
		add_summary("Blower9 OK. " )
	else:
		add_summary("Blower9 NOT OK. ")
		nagios_status(warning)
	
	# Check blower 10
	if blower10state == "1":
		nagios_status(ok)
		add_summary("Blower10 OK. " )
	else:
		add_summary("Blower10 NOT OK. ")
		nagios_status(warning)
	
	if blower1state != "1" and blower2state != "1" and blower3state != "1" and blower4state != "1" and blower5state != "1" and blower6state != "1" and blower7state != "1" and blower8state != "1" and blower9state != "1" and blower10state != "1":
		nagios_status(critical)
	

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
	
	# Check SwitcModule Communications
	if not oids.has_key(bistSwitchModulesCommunicating) or not oids.has_key(bistSwitchModulesInstalled):
		add_summary( "SwitchModules N/A. ")
	if oids[bistSwitchModulesCommunicating] == oids[bistSwitchModulesInstalled]:
		nagios_status(ok)
		add_summary("Switchmodules OK. ")
	else:
		nagios_status(warning)
		add_summary( "Switchmodules NOT OK. ")
	# Check blower status
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
		elif opts.mode == 'blowers':
			check_blowers()
		elif opts.mode == 'switchmodules':
			check_switchmodules()
		else:
			parser.error("%s is not a valid option for --mode" % opts.mode)
	except Exception, e:
		print "Unhandled exception while running script: %s" % e
		exit(unknown)
	end()

