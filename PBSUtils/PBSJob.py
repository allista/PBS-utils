# coding=utf-8
#
# Copyright (C) 2012 Allis Tauri <allista@gmail.com>
# 
# PBS Utils is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# indicator_gddccontrol is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
'''
Created on Dec 2, 2013

@author: Allis Tauri <allista@gmail.com>
'''

import os
import abc
import time
import shutil
import subprocess
import argparse
from ConfigParser import SafeConfigParser
from SerialJobFactory import SerialJobFactory

class PBSJob(object):
    '''Base class for PBS jobs'''
    __metaclass__ = abc.ABCMeta
    
    _bin         = None
    _name        = None
    _description = None

    def __init__(self):
        #init members and restore configuration
        self._args      = None
        self._host      = None
        self._walltime  = None
        self._email     = os.getenv('DEBEMAIL')
        self._save_jobs = False        
        self._restore_settings()
        #standard messages
        _conf_msg  = ('You don\'t have to call %s with this '
                      'option each time: the value is stored '
                      'in %s.' % (self._name, self._config_file()))
        _setto_msg = ' Currently is set to %s.'
        #argument parser
        self._parser = argparse.ArgumentParser(prog=self._name,
                                               description=self._description)
        self._add_nodes_argument()
        self._parser.add_argument('-W','--walltime', metavar='HH:MM:SS', 
                                  type=str, nargs=1,
                                  help='Job time limit.')
        self._parser.add_argument('-M','--mail-address', metavar='you@domain.com', 
                                  type=str, nargs=1,
                                  help=('E-mail address to send job status '
                                         'notifications. If you don\'t want to '
                                         'receive them, set to "". '+_conf_msg+
                                         (_setto_msg % self._email if self._email 
                                          else ' Currently not set.')))
        self._parser.add_argument('-E','--executable', metavar='path', 
                                  type=str, nargs=1,
                                  help=('Path to the executable. '+_conf_msg+
                                         _setto_msg % self._bin))
        self._parser.add_argument('--save-job-script', 
                                  action='store_true', default=False,
                                  help='Save job script to a file. May be useful '
                                  'to analyze problems or resubmit the same job later.')
    #end def
    
    def _add_nodes_argument(self):
        self._parser.add_argument('-N','--nodes', metavar='nodes', 
                                  type=str, nargs=1,
                                  help='PBS node specification.')
    #end def
    
    def parse_args(self): 
        self._args      = self._parser.parse_args()
        self._walltime  = self._args.walltime[0] if self._args.walltime else None
        if self._args.mail_address:
            self._email = self._args.mail_address[0]
        self._save_jobs = self._args.save_job_script 
        if self._args.executable:
            self._bin   = self._args.executable[0]
        self._save_settings()
    #end def
    
    
    @abc.abstractmethod
    def submit(self):
        if not self._args:
            raise RuntimeWarning('PBSJob._new_job: arguments were not parsed yet.')
    #end def
    
    def _submit_job(self, job_file):
        try: qsub = subprocess.Popen(('qsub', job_file))
        except OSError: print '\nFaild to execute qsub'
        qsub.wait()
        if self._save_jobs: shutil.copy(job_file, './')
        os.unlink(job_file)
        #wait a second for PBS to get stagein files from jf's tmp dir
        time.sleep(1)
    #end def
    
    
    @classmethod
    def _config_file(cls):
        home = os.path.expanduser('~')
        return os.path.join(home, '.pbs_utils.conf')
    #end def
    
    @classmethod
    def _get_config(cls):
        if not cls._name: return
        config = SafeConfigParser()
        if not config.read(cls._config_file()): return None
        return config
    #end def
    
    def _restore_settings(self):
        config = self._get_config()
        if config is None: return
        #read in options
        if config.has_option('common', 'email'):
            self._email = config.get('common', 'email').decode('UTF-8')
        #read in options
        if config.has_option(self._name, 'executable'):
            self._bin = config.get(self._name, 'executable').decode('UTF-8')
    #end def
    
    def _save_settings(self):
        config = self._get_config()
        if config is None: 
            config = SafeConfigParser()
        #setup common and program sections
        if not config.has_section('common'):
            config.add_section('common')
        if not config.has_section(self._name):
            config.add_section(self._name)
        #set options
        config.set('common', 'email', unicode(self._email).encode('UTF-8'))
        config.set(self._name, 'executable', unicode(self._bin).encode('UTF-8'))
        #save
        config.write(open(self._config_file(), 'wb'))
    #end def
#end def


class BatchFileJob(PBSJob):
    _extension = None
    
    def __init__(self):
        super(BatchFileJob, self).__init__()
        if self._extension and self._extension[0] != '.':
            self._extension = '.'+self._extension
        self._parser.add_argument('files', metavar='file', 
                                  type=str, nargs='+',
                                  help='Path to a file%s' % self._extension)
    #end def
    
    def parse_args(self):
        super(BatchFileJob, self).parse_args()
        for fname in self._args.files:
            if not os.path.isfile(fname):
                raise ValueError('No such file: %s' % fname)
    #end def
    
    def submit(self):
        super(BatchFileJob, self).submit()
        for _file in self._args.files:
            #go to the file
            wdir = os.path.dirname(_file)
            if wdir:
                os.chdir(wdir)
                _file = os.path.basename(_file)
            #create and submit job
            job_file = self._new_job(_file)
            if not job_file: continue
            self._submit_job(job_file)
    #end def
    
    @abc.abstractmethod
    def _new_job(self, _file): pass
#end class


class SerialJob(PBSJob):
    def parse_args(self):
        super(SerialJob, self).parse_args()
        self._host = self._args.host[0] if self._args.host else None
        self._jf   = SerialJobFactory(self._name, 
                                      host=self._host, 
                                      email=self._email)
    #end def

    def _add_nodes_argument(self):
        self._parser.add_argument('-H','--host', metavar='hostname', 
                                  type=str, nargs=1,
                                  help='The host at which job should be run. '
                                  'If not provided, first available node is used.')
    #end def
#end class