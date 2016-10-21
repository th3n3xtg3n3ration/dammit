#!/usr/bin/env python

from collections import OrderedDict
from os import mkdir, path

from doit.cmd_base import TaskLoader
from doit.doit_cmd import DoitMain
from doit.dependency import Dependency, SqliteDB

from .profile import StartProfiler
from .utils import Move
from . import ui

class TaskHandler(TaskLoader):

    def __init__(self, directory, logger, config=None, files=None, 
                 profile=False, db=None, **doit_config_kwds):

        super(TaskHandler, self).__init__()

        if files is None:
            self.files = {}
        elif type(files) is not dict:
            raise TypeError('files must be of type dict')
        else:
            self.files = files

        self.tasks = OrderedDict()
        
        self.directory = directory
        try:
            mkdir(directory)
        except OSError:
            pass

        if db is None:
            dep_file = path.join(self.directory, 'doit.db')
        else:
            dep_file = path.join(self.directory, '{0}.doit.db'.format(db))
        self.dep_file = dep_file
        logger.debug('Dependency Database File: {0}'.format(dep_file))
        self.doit_config = dict(dep_file=self.dep_file, **doit_config_kwds)
        self.doit_dep_mgr = Dependency(SqliteDB, dep_file)

        self.profile = profile
        self.logger = logger
        

    def register_task(self, name, task, files=None):
        if files is None:
            files = {}
        if type(files) is not dict:
            raise TypeError('files must be of type dict')
        
        self.tasks[name] = task
        self.files.update(files)
        self.logger.debug('registered task {0}: {1}\n'
                          '  with files {2}'.format(name, task, files))

    def clear_tasks(self):
        self.logger.debug('Clearing {0} tasks'.format(len(self.tasks)))
        self.tasks = {}

    def get_status(self, task):
        if type(task) is str:
            try:
                task = self.tasks[task]
            except KeyError:
                self.logger.error('Task not found:{0}'.format(task))
                raise
        self.logger.debug('Getting status for task {0}'.format(task.name))
        status = self.doit_dep_mgr.get_status(task, self.tasks.values(),
                                              get_log=True)
        self.logger.debug('Task {0} had status {1}'.format(task, status.status))
        try:
            self.logger.debug('Task {0} had reasons {1}'.format(task, status.reasons))
        except AttributeError:
            pass

        return status.status

    def print_statuses(self, uptodate_msg='All tasks up-to-date!'):
        uptodate, statuses = self.check_uptodate()
        if uptodate:
            print(ui.paragraph(uptodate_msg))
        else:
            uptodate_list = [t for t,s in statuses.items() if s is True]
            outofdate_list = [t for t,s in statuses.items() if s is False]
            if uptodate_list:
                print('\nUp-to-date tasks:')
                print(ui.listing(uptodate_list))
            if outofdate_list:
                print('\nOut-of-date tasks:')
                print(ui.listing(outofdate_list))
        return uptodate, statuses

    def check_uptodate(self):
        with Move(self.directory):
            statuses = {}
            outofdate = False
            for task_name, task in self.tasks.items():
                status = self.get_status(task)
                statuses[task_name] = status == 'up-to-date'
            return all(statuses.values()), statuses
        
    def load_tasks(self, cmd, opt_values, pos_args):
        self.logger.debug('loading {0} tasks'.format(len(self.tasks)))
        return self.tasks.values(), self.doit_config

    def run(self, doit_args=None):
        if doit_args is None:
            doit_args = ['run']
        runner = DoitMain(self)

        with Move(self.directory):
            if self.profile is True:
                profile_fn = path.join(self.directory, 'profile.csv')
                with StartProfiler(filename=profile_fn):
                    return runner.run(doit_args)
            else:
                return runner.run(doit_args)

