#!/usr/bin/python
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

import shutil, os, socket
from datetime import datetime
from tempfile import mkdtemp, NamedTemporaryFile

class SerialJobFactory(object):
    '''Generates PBS job scripts'''
    
    _nodes_file = '/var/spool/torque/server_priv/nodes'
    _nodes      = dict()
    _min_ppn    = None
    
    def __init__(self, name, host=None, walltime=None, restartable=False, stagein_files=None,):
        self._init_nodes()
        self._name        = '%s-%s' % (name, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        self._host        = self._host(host)
        self._walltime    = walltime
        self._restartable = restartable
        self._stagin      = stagein_files
        self._wdir        = os.getcwd()
        self._email       = os.getenv('DEBEMAIL')
        self._hostname    = socket.gethostname()
        self._prepare_stagein()
    #end def
    
    def __del__(self):
        if hasattr(self, '_tmpdir'): 
            shutil.rmtree(self._tmpdir)
    #end def
        
    @classmethod
    def _init_nodes(cls):
        if cls._nodes: return
        for line in open(cls._nodes_file, 'r').readlines():
            host = line.strip().split()
            ppn, props = 1, []
            for prop in host[1:]:
                if prop[:3] == 'np=':
                    ppn = int(prop[3:])
                    if cls._min_ppn is None \
                    or ppn < cls._min_ppn: 
                        cls._min_ppn = ppn
                else: props.append(prop)
            cls._nodes[host[0]] = {'ppn':ppn, 'props':props}
    #end def
        
    @classmethod
    def _host(cls, host):
        if not host: return '1:ppn=%d' % cls._min_ppn
        if host not in cls._nodes:
            raise ValueError('JobFactory._host: no such host in the cluster')
        return '%s:ppn=%d' % (host, cls._nodes[host]['ppn'])
    #end def
    
    def _prepare_stagein(self):
        if not self._stagin: return
        self._tmpdir = mkdtemp(prefix=self._name+'-setup-')
        for i, f in enumerate(self._stagin):
            if os.path.isfile(f):
                shutil.copy(f, self._tmpdir)
                self._stagin[i] = os.path.join(self._tmpdir, os.path.basename(f))
            else: raise OSError('SerialJobFactory._prepare_stagein: no such file: %s' % f)
    #end def
    
    def create_job(self, commands):
        if not commands: raise ValueError('SerialJobFactory.create_job: commands '
                                          'should be a non-empty list of strings')
        job_file = NamedTemporaryFile(prefix=self._name+'-',
                                      suffix='.job',
                                      delete=False)
        #name, stdin/stdout, nodes, etc...
        job_file.writelines(['#!/bin/bash\n',
                             '#PBS -N %s\n'     % self._name,
                             '#PBS -o %s.out\n' % self._name,
                             '#PBS -e %s.err\n' % self._name,
                             '#PBS -c enabled,shutdown,periodic\n',
                             '#PBS -r %s\n' %('y' if self._restartable else 'n'),
                             '#PBS -l nodes=%s\n' % self._host])
        #optional
        if self._walltime:
            job_file.write('#PBS -l walltime=%s\n' % self._walltime)
        if self._email:
            job_file.write('#PBS -m ae -M %s\n' % self._email)
        #stageins
        if self._stagin:
            for f in self._stagin:
                job_file.write('#PBS -W stagein="$TMPDIR/%(basename)s@%(runner)s:%(path)s"\n'
                               % {'basename': os.path.basename(f),
                                  'runner': self._hostname,
                                  'path': f})
        job_file.write('\n')
        #write commands
        for cmd in commands: job_file.write(cmd+'\n')
        #copy all output files back to the working directory
        job_file.write('scp * %(runner)s:%(wdir)s/' % {'runner': self._hostname,
                                                       'wdir': self._wdir})
        job_file.close()
        return job_file.name
    #end def
#end class


#tests
if __name__ == '__main__':
    jf = SerialJobFactory('test_job', stagein_files=['../README'])
    job_file = jf.create_job(['ls'])
    print job_file
    for line in open(job_file, 'r').readlines():
        print line.strip()
    os.unlink(job_file)