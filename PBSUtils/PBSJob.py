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
import subprocess
import argparse

class PBSJob(object):
    '''Base class for PBS jobs'''
    __metaclass__ = abc.ABCMeta
    
    _bin         = ''
    _name        = None
    _description = None

    def __init__(self):
        self._parser = argparse.ArgumentParser(prog=self._name,
                                               description=self._description)
        self._parser.add_argument('-H','--host', metavar='hostname', 
                                  type=str, nargs=1,
                                  help='one of the hosts in a cluster')
        self._parser.add_argument('-W','--walltime', metavar='HH:MM:SS', 
                                  type=str, nargs=1,
                                  help='job time limit')
        self._args = None
    #end def
    
    def parse_args(self): 
        self._args     = self._parser.parse_args()
        self._host     = self._args.host[0] if self._args.host else None
        self._walltime = self._args.walltime[0] if self._args.walltime else None
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
    #end def
    
    @classmethod
    def _is_exe(cls, fname):
        return os.path.isfile(fname) and os.access(fname, os.X_OK)
    
    @classmethod
    def _which(cls, _bin):
        fpath, _fname = os.path.split(_bin)
        if fpath:
            if not cls._is_exe(_bin):
                raise RuntimeError('%s is not executable' % _bin)
            return _bin
        else:
            for path in os.environ["PATH"].split(os.pathsep):
                path = path.strip('"')
                exe_file = os.path.join(path, _bin)
                if cls._is_exe(exe_file):
                    return exe_file
            raise RuntimeError('%s was not found in the PATH' % _bin)
    #end def
    
    @classmethod
    def _init_bin(cls):
        if not cls._bin: return
        cls._bin = cls._which(cls._bin)
    #end def
#end def


class BatchFileJob(PBSJob):
    def __init__(self):
        super(BatchFileJob, self).__init__()
        self._parser.add_argument('files', metavar='path', 
                                  type=str, nargs='+',
                                  help='File(s) to process.')
    #end def
    
    def parse_args(self):
        PBSJob.parse_args(self)
        for fname in self._args.files:
            if not os.path.isfile(fname):
                raise ValueError('No such file: %s' % fname)
    #end def
#end class