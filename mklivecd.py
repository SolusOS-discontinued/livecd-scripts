#!/usr/bin/env python

from solusos.live.fstools import FilesystemCreator
from solusos.console import *
from solusos.system import SystemManager
from solusos.live.pisimaker import PisiMaker
from os import system as execute_hide

import sys
from optparse import OptionParser
import os
import os.path
import shutil
import time
import glob

try:
	from configobj import ConfigObj
except:
	print "Install ConfigObj before running!"
	sys.exit (1)

REPO_URI = "http://packages.solusos.com/2/pisi-index.xml.xz"
RESOURCE_DIR = "/usr/share/solusos/resources_2"

class MediaCreator:
	
	def __init__(self, config_file):
		self.config = ConfigObj (config_file)
		HOME = os.path.abspath (os.environ['HOME']) if "SUDO_USER" not in os.environ else "/home/%s/" % os.environ['SUDO_USER']
        
		self.workDir = self.config["Project"]["WorkDir"].replace("{{HOME}}", HOME)
		self.mountpoint = os.path.join (self.workDir, "local_root")
		self.build_dir = os.path.join (self.workDir, "build").replace("{{HOME}}", HOME)
		self.live_os = os.path.join (self.build_dir, "LiveOS")
		self.img_dir = os.path.join (self.workDir, "LiveOS")
		self.dist_dir = self.config["Project"]["DistFiles"].replace("{{HOME}}", HOME)
		self.output_file = self.config ["Project"]["ISO"].replace("{{HOME}}", HOME)
		for needed in [self.workDir, self.mountpoint, self.img_dir]:
			if not os.path.exists (needed):
				os.mkdir (needed)
	
	def work_it(self):
		''' Do the actual grunt work '''
		self.filesystem = self.config["Media"]["Filesystem"]
		self.fs_image = os.path.join (self.workDir, "LiveOS/rootfs.img")
		# Permanent assumption
		size = int(self.config["Media"]["Size"])
		if os.path.exists (self.fs_image):
			return
		print_info ("Creating %s image at %s" % (self.filesystem, self.fs_image))	
		FilesystemCreator.create_image (size=size, path=self.fs_image, filesystem=self.filesystem)
	
	def enter_system (self):
		SystemManager.mount (self.fs_image, self.mountpoint, filesystem=self.filesystem, options="loop")
	
	def exit_system (self):
		SystemManager.umount (self.mountpoint)
	
	def install_system (self):
		PisiMaker.AddRepository ("SolusOS", REPO_URI, target_directory=self.mountpoint)
		PisiMaker.InstallPackages (["libgcrypt", "shared-mime-info", "desktop-file-utils", "hicolor-icon-theme"], target_directory=self.mountpoint, safety=False)
		PisiMaker.InstallComponent ("system.boot", target_directory=self.mountpoint)
		PisiMaker.InstallComponent ("xorg.library", target_directory=self.mountpoint)
		PisiMaker.InstallComponent ("system.base", target_directory=self.mountpoint, safety=True)
		PisiMaker.InstallPackages (["kernel", "kernel-modules", "sqlite3", "lvm2"], target_directory=self.mountpoint, safety=True)
		for component in ["desktop.xfce", "xorg.display", "xorg.server", "xorg.driver"]:
			PisiMaker.InstallComponent (component, target_directory=self.mountpoint)
		additional_packages = "software-update-icon solusos-branding plymouth inxi pulseaudio alsa-plugins alsa-firmware libical libjson-glib firefox thunderbird udisks hexchat gedit galculator file-roller eog gnome-packagekit gsettings-desktop-schemas gnome-icon-theme-symbolic polkit-gnome alsa-lib abiword gnumeric linux-firmware wpa_supplicant gnome-keyring gcr librsvg hicolor-icon-theme lightdm-gtk-greeter elementary-icon-theme libgnome-keyring network-manager gnome-icon-theme llvm network-manager-applet gvfs"
		PisiMaker.InstallPackages (additional_packages.split(" "), target_directory=self.mountpoint, safety=True)

		installer_deps = "os-installer"
		PisiMaker.InstallPackages (installer_deps.split(" "), target_directory=self.mountpoint, safety=True)

		# Configure Plymouth
		cmd = "plymouth-set-default-theme solusos"
		execute_hide ("chroot \"%s\" %s" % (self.mountpoint, cmd))

		self.add_accounts ()
		PisiMaker.configure_system (self.mountpoint)

		# initramfs hacks
		initramfs = os.path.join (self.dist_dir, "boot/initrd.img")
		source_initramfs = os.path.join (self.mountpoint, "boot/initramfs-3.11.0.img")
		shutil.copy (source_initramfs, initramfs)

		# polkit fix
		polkit = os.path.join (self.mountpoint, "var/empty")
		if not os.path.exists (polkit):
			os.makedirs (polkit)

		kernel = os.path.join (self.dist_dir, "boot/kernel")
		source_kernel = os.path.join (self.mountpoint, "boot/kernel-3.11.0")
		shutil.copy (source_kernel, kernel)

		shutil.copytree (self.dist_dir, self.build_dir)
		os.mkdir (self.live_os)

		self.dbus_configure ()
		self.configure_system_accounts()
	
	def build_cd (self):
		cwd = os.getcwd ()

		# Check filesystem for issues.
		os.system ("e2fsck -y %s" % self.fs_image);

		squash_file = os.path.join (self.live_os, "squashfs.img")
		os.chdir (self.img_dir)
		#os.system ("mksquashfs -keep-as-directory %s %s" % (self.fs_image.split("/")[-1], squash_file))
		os.system ("mksquashfs %s %s -keep-as-directory -comp xz" % (".", squash_file))

		description = "SolusOS2"

		os.chdir (self.workDir)
        
		cmd = "genisoimage -o %(OutputFile)s \
-no-emul-boot -boot-load-size 4 -boot-info-table \
-b isolinux/isolinux.bin -c isolinux/boot.cat \
-V \"%(Description)s\" -cache-inodes  -r -J  -l \
%(OutputDir)s" % { 'OutputFile': self.output_file, 'Description': description, 'OutputDir': self.build_dir }

		os.system (cmd)
		cmd = "isohybrid %s" % self.output_file
		os.system (cmd)

	def add_accounts(self):
		baselayout = os.path.join (self.mountpoint, "usr/share/baselayout")
		target = os.path.join (self.mountpoint, "etc")

		for item in os.listdir (baselayout):
			try:
			    shutil.copy2(os.path.join(baselayout, item), os.path.join(target, item))
			except Exception,e:
			    print  e

		# set up dbus account
		dbus_id = 18
		dbus_name = "messagebus"
		dbus_desc = "D-Bus Message Daemon"
		dbus_command1 = "groupadd -g %d %s" % (dbus_id, dbus_name)
		dbus_command2 = "useradd -m -d /var/run/dbus -r -s /bin/false -u %d -g %d %s -c \"%s\"" % (dbus_id, dbus_id, dbus_name, dbus_desc)
		execute_hide ("chroot \"%s\" %s" % (self.mountpoint, dbus_command1))
		execute_hide ("chroot \"%s\" %s" % (self.mountpoint, dbus_command2))


	def configure_system_accounts(self):
		# Create the default user account
		cmd = "useradd -m -s /bin/bash -c \"%s\" %s" % ("Live User", "live")
		execute_hide("chroot \"%s\" %s" % (self.mountpoint, cmd))

		# Set an empty password for live user
		execute_hide("chroot \"%s\" /bin/bash --login -c \"%s\"" % (self.mountpoint, "echo 'live:' |chpasswd"))

		# Finally, add the user to the right groups
		cmd = "usermod -a -G %s %s" % ("sudo,audio,video,cdrom", "live")
		execute_hide("chroot \"%s\" %s" % (self.mountpoint, cmd))

		# Modify sudoers so that live user is not asked for a password
		sudoers = os.path.join(self.mountpoint, "etc/sudoers")
		line = "%live ALL=(ALL) NOPASSWD:ALL"
		cmd = "echo \"%s\" >> /etc/sudoers" % line
		execute_hide("chroot \"%s\" /bin/bash --login -c '%s'" % (self.mountpoint, cmd))

		# Set lightdm to automatically login
		login_file = os.path.join(self.mountpoint, "etc/lightdm/lightdm.conf")
		cmd1 = "replace \"#autologin-user=\" \"autologin-user=live\" -- %s" % login_file
		cmd2 = "replace \"#autologin-user-timeout=0\" \"autologin-user-timeout=0\" -- %s" % login_file
		cmd3 = "replace \"#user-session=default\" \"user-session=xfce\" -- %s" % login_file

		os.system(cmd1)
		os.system(cmd2)
		os.system(cmd3)

	def dbus_configure(self):
		# D-BUS.
		self.dbus_pid = os.path.join (self.mountpoint, "var/run/dbus/pid")
		if os.path.exists (self.dbus_pid):
			print_info ("Deleting stale D-BUS PID file..")
			os.unlink (self.dbus_pid)

		
		# Always ensure the dbus start files exist
		lsb_init = os.path.join (self.mountpoint, "lib/lsb")
		dbus_rc = os.path.join (self.mountpoint, "etc/rc.d/init.d")
		if not os.path.exists (lsb_init):
			source_lsb = os.path.join (RESOURCE_DIR, "data/lsb")
			dest_lsb = os.path.join (self.mountpoint, "lib/lsb")
			print_info ("Copying lsb init functions")
			shutil.copytree (source_lsb, dest_lsb)
		
		if not os.path.exists (dbus_rc):
			source_dbus = os.path.join (RESOURCE_DIR, "data/init.d")
			dest_dbus = os.path.join (self.mountpoint, "etc/rc.d/init.d")
			print_info ("Copying dbus startup files")
			shutil.copytree (source_dbus, dest_dbus)
		
		# Startup dbus
		self.dbus_service = "/etc/rc.d/init.d/dbus"
		print_info ("Starting the D-Bus systemwide message bus")
		execute_hide ("chroot \"%s\" \"%s\" start" % (self.mountpoint, self.dbus_service))

		# Check for urandom
		urandom = os.path.join (self.mountpoint, "dev/urandom")
		if not os.path.exists (urandom):
			execute_hide ("chroot \"%s\" mknod -m 644 /dev/urandom c 1 9" % self.mountpoint)

		# FIX: dbus
		execute_hide ("chroot \"%s\" chmod o+x /usr/lib/dbus-1.0/dbus-daemon-launch-helper" % self.mountpoint)

		# Set up devices + stuff
		self.dev_shm_path = os.path.join (self.mountpoint, "dev/shm")
		if not os.path.exists (self.dev_shm_path):
			os.makedirs (self.dev_shm_path)
		
		self.proc_dir = os.path.join (self.mountpoint, "proc")
		SystemManager.mount ("tmpfs", self.dev_shm_path, filesystem="tmpfs")
		SystemManager.mount ("proc", self.proc_dir, filesystem="proc")

        ### ADD DBUSY TYPE STUFF HERE ####
		execute_hide ("chroot \"%s\" pisi configure-pending" % self.mountpoint)

		dbus_pid = os.path.join (self.mountpoint, "var/run/dbus/pid")
		print_info ("Stopping D-BUS...")
		
		with open (dbus_pid, "r") as pid_file:
			pid = pid_file.read().strip()
			os.system ("kill -9 %s" % pid)
		# Safety, gives dbus enough time to die
		time.sleep (3)
		
		# Murder the remaining processes
		print_info ("Asking all remaining processes to stop...")
		self.murder_death_kill (be_gentle=True)
		print_info ("Force-kill any remaining processes...")
		self.murder_death_kill ()
		
		print_info ("Unmounting virtual filesystems...")				
		SystemManager.umount (self.dev_shm_path)
		SystemManager.umount (self.proc_dir)

	def murder_death_kill (self, be_gentle=False):
		''' Completely and utterly murder all processes in the chroot :) '''
		for root in glob.glob ("/proc/*/root"):
			try:
				link = os.path.realpath (root)
				if os.path.abspath (link) == os.path.abspath (self.mountpoint):
					pid = root.split ("/")[2]
					if be_gentle:
						os.system ("kill %s" % pid)
					else:
						os.system ("kill -9 %s" % pid)
			except:
				pass

if __name__ == "__main__":
	parser = OptionParser()
	parser.add_option ("-c", "--config", dest="config", help="configuration file", default="sample.conf")
	(options, args) = parser.parse_args()
	
	m = MediaCreator (options.config)
	print_header ("SolusOS 2 LiveCD Creator", None)
	m.work_it ()
	m.enter_system ()
	m.install_system ()
	m.exit_system ()
	m.build_cd ()
