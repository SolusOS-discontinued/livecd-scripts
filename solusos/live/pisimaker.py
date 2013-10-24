import os
#from solusos.system import execute_hide
from os import system as execute_hide
from solusos.console import *

def chroot_call (directory, command):
	execute_hide ("chroot \"%s\" /bin/bash -c \"%s\"" % (directory, command))

class PisiMaker:
	
	@staticmethod
	def AddRepository (name, url, target_directory="FAIL"):
		print_info ("Adding repository...", "+")
		execute_hide ("pisi add-repo %s %s -D %s" % (name, url, target_directory))
	
	@staticmethod
	def InstallComponent (component, target_directory="FAIL", safety=False):
		print_info ("Installing component: %s" % component, "+")
		if not safety:
			execute_hide ("pisi install --yes-all --ignore-comar --ignore-safety -c %s -D %s" % (component, target_directory))
		else:
			execute_hide ("pisi install --yes-all --ignore-comar -c %s -D %s" % (component, target_directory))
		execute_hide ("pisi delete-cache -D %s" % target_directory)
	
	@staticmethod
	def InstallPackages (pkgs, target_directory="FAIL", safety=False):
		packages = " ".join (pkgs)
		print_info ("Installing packages: %s" % ", ".join(pkgs), "+")
		if not safety:
			execute_hide ("pisi install --yes-all --ignore-comar --ignore-safety %s -D %s" % (packages, target_directory))
		else:
			execute_hide ("pisi install --yes-all --ignore-comar %s -D %s" % (packages, target_directory))
		execute_hide ("pisi delete-cache -D %s" % target_directory)
					
	@staticmethod
	def configure_system (directory):
		print_info ("Resync modules and libraries..")
		chroot_call (directory, "/sbin/ldconfig")
		chroot_call (directory, "/sbin/depmod 3.11.0")
		
		chroot_call (directory, "dracut --help")		
		cmd = "dracut --kver 3.11.0 --force --xz --add \"dmsquash-live systemd pollcdrom\" --add-drivers \"squashfs ext3 ext2 vfat msdos sr_mod sd_mod ide-cd cdrom ehci_hcd uhci_hcd ohci_hcd usb_storage usbhid dm_mod device-mapper ata_generic libata\""
		chroot_call (directory, cmd)
		execute_hide ("pisi delete-cache -D %s" % directory)
