#!/usr/bin/python
# coding=utf-8

'''
Created on Dec 2, 2013

@author: Allis Tauri <allista@gmail.com>
'''

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
import os
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

from distutils.core import setup
setup(name='PBS-utils',
      version='1.1',
      description=('Utility scripts to run arbitrary bioinformatics software '
                   'on a PBS server'),
      long_description=read('README'),
      license='GPL-3',
      author='Allis Tauri',
      author_email='allista@gmail.com',
      #url='https://launchpad.net/',
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Intended Audience :: Science/Research',
        'Operating System :: POSIX',
        'Programming Language :: Python'],
      packages=['PBSUtils'],
      scripts=['mb_run', 'garli_run', 'degen_primer_run'],
      )