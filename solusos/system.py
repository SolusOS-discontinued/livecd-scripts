import os
import os.path

from solusos.console import *
import subprocess

def sizeof_fmt(num):
        for x in ['bytes','KB','MB','GB']:
                if num < 1024.0:
                        return "%3.1f%s" % (num, x)
                num /= 1024.0
        return "%3.1f%s" % (num, 'TB')

def execute_hide (command):
	''' Execute a command with no stdout '''
	p = subprocess.Popen (command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	p.wait ()
		
class SystemManager:
	
	@staticmethod
	def mount (device, mountpoint, filesystem=None, options=None):
		if filesystem is not None:
			cmd = "mount -t %s %s %s" % (filesystem, device, mountpoint)
		else:
			cmd = "mount %s %s" % (device, mountpoint)
		if options is not None:
			cmd += " -o %s" % options
		os.system (cmd)
		
	@staticmethod
	def umount (device_or_mount):
		cmd = "umount \"%s\"" % device_or_mount
		os.system (cmd)
		
	@staticmethod
	def mount_home (point):
		os.system ("mount --bind /home/ \"%s\"" % point)
