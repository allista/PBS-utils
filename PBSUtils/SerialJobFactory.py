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
    '''Generates serial (i.e. for a single node only) PBS job scripts'''
    
    _nodes_file = '/var/spool/torque/server_priv/nodes'
    _nodes      = dict()
    _min_ppn    = None
    
    def __init__(self, name, host=None, email=None):
        self._init_nodes()
        self._name     = self._time_name(name)
        self._host     = self._host(host)
        self._email    = email
        self._hostname = socket.gethostname()
        self._tmpdir   = mkdtemp(prefix=self._name+'-setup-')
    #end def
    
    def __del__(self): pass
#        if hasattr(self, '_tmpdir'):
#            shutil.rmtree(self._tmpdir)
    #end def
    
    @classmethod
    def _time_name(cls, name):
        return '%s-%s' % (name, datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        
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
            raise ValueError('SerialJobFactory._host: no such host in the cluster.\n'+
                             'Available hosts are: %s' % ' '.join(cls._nodes.keys()))
        return '%s:ppn=%d' % (host, cls._nodes[host]['ppn'])
    #end def
    
    def _prepare_stagein(self, stagein):
        stagein_dict  = dict()
        for i, f in enumerate(stagein):
            if os.path.isfile(f):
                shutil.copy(f, self._tmpdir)
                basef = os.path.basename(f)
                if not os.path.isfile(os.path.join(self._tmpdir, basef)):
                    raise OSError('SerialJobFactory._prepare_stagein: '+
                                  'unable to copy file: %s' % f)
                stagein_dict['file%d'%(i+1)] = basef
            else: raise OSError('SerialJobFactory._prepare_stagein: no such file: %s' % f)
        return stagein_dict
    #end def
    
     
    
    def create_job(self, commands, name=None, walltime=None, restartable=False, stagein_files=None):
        if not commands: raise ValueError('SerialJobFactory.create_job: commands '
                                          'should be a non-empty list of strings')
        if not name: name = self._name
        else: name = self._time_name(name)
        job_file = NamedTemporaryFile(prefix=name+'-',
                                      suffix='.job',
                                      delete=False)
        #name, stdin/stdout, nodes, etc...
        job_file.writelines(['#!/bin/bash\n',
                             '#PBS -N %s\n'     % name,
                             '#PBS -o %s.out\n' % name,
                             '#PBS -e %s.err\n' % name,
                             '#PBS -c enabled,shutdown,periodic\n',
                             '#PBS -r %s\n' %('y' if restartable else 'n'),
                             '#PBS -l nodes=%s\n' % self._host])
        #optional
        if walltime:
            job_file.write('#PBS -l walltime=%s\n' % walltime)
        if self._email:
            job_file.write('#PBS -m abe -M %s\n' % self._email)
        #stageins
        if stagein_files:
            stagein_files = self._prepare_stagein(stagein_files)
            for f in stagein_files.values():
                job_file.write('#PBS -W stagein="$TMPDIR/%(basename)s@%(runner)s:%(path)s"\n'
                               % {'basename': f,
                                  'runner': self._hostname,
                                  'path': os.path.join(self._tmpdir, f)})
        job_file.write('\n')
        #write commands
        job_file.write('cd $TMPDIR\n')
        for cmd in commands:
            try: cmd = cmd % stagein_files
            except TypeError: pass
            job_file.write(cmd+'\n')
        #copy all output files back to the working directory
        job_file.write('scp * %(runner)s:%(wdir)s/' % {'runner': self._hostname,
                                                       'wdir': os.getcwd()})
        job_file.close()
        return job_file.name
    #end def
#end class


#tests
if __name__ == '__main__':
    jf = SerialJobFactory('test_job')
    job_file = jf.create_job(['ls %(file1)s'], name='test_job1', stagein_files=['../README'])
    del jf
    
    print job_file
    for line in open(job_file, 'r').readlines():
        print line.strip()
    os.unlink(job_file)
