import os

class FilesystemCreator:
	''' Used to create LiveOS filesystem stuffs '''
	
	@staticmethod
	def create_image (size=0, path=None, filesystem=None):
		cmd = "dd if=/dev/zero of=\"%s\" bs=1M count=%d" % (path, size)
		os.system (cmd)
		cmd = "mkfs -t %s -F \"%s\"" % (filesystem, path)
		os.system (cmd)
		
