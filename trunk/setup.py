#!/usr/bin/env python

from distutils.core import setup
from distutils.command.install_lib import install_lib
import glob
import os

class InstallLib(install_lib):
    def install(self):
	install = self.distribution.get_command_obj('install')
	installed_template = 'data_dir =  "'+ os.path.join(install.prefix, 'share', 'khagan')+'"'

	filename = os.path.join(self.install_dir, 'khagan_globals.py')
        self.mkpath(os.path.dirname(filename))
        fp = open(filename, 'w')
        fp.write(installed_template)
        fp.close()
	return install_lib.install(self) + [filename]

setup(name='Khagan',
      version='0.1',
      description='Khagan is a live user interface builder for controling parameters via OSC',
      author='Loki Davison',
      author_email='loki.davison@gmail.com',
      url='http://khagan.berlios.de',
      py_modules = ['osc'],
      scripts = ['khagan.py'],
      data_files=[('share/khagan', ['khagan.glade']), ('share/khagan/examples', glob.glob('examples/*'))],
      cmdclass={'install_lib': InstallLib})

