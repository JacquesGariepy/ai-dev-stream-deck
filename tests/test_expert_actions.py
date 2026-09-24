import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from aidev import git_actions, project_tasks
from aidev.storage import save_settings


def git(folder,*args):
    subprocess.run(['git','-C',str(folder),*args],check=True,capture_output=True)


@unittest.skipUnless(shutil.which('git'),'Git required')
class GitActionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.data=Path(self.temp.name)/'data';self.repo=Path(self.temp.name)/'repo';self.repo.mkdir()
        patcher=patch.dict(os.environ,{'AI_DEV_DATA_DIR':str(self.data)});patcher.start();self.addCleanup(patcher.stop)
        git(self.repo,'init','-q','-b','main');git(self.repo,'config','user.email','t@example.com');git(self.repo,'config','user.name','T')
        (self.repo/'a.txt').write_text('a');git(self.repo,'add','.');git(self.repo,'commit','-qm','init')
        save_settings({'project':str(self.repo)})

    def test_fixed_commands_launch_visible_tasks_with_exact_arguments(self):
        with patch('aidev.project_tasks.launch') as launch:
            git_actions.run('pull')
        task=launch.call_args[0][0]
        self.assertEqual(task['arguments'],['pull','--ff-only'])
        self.assertEqual(Path(task['project']),self.repo.resolve())
        self.assertTrue(Path(task['executable']).is_file())
        with self.assertRaises(ValueError):git_actions.run('reset-hard')

    def test_push_plan_sets_upstream_only_with_origin(self):
        with self.assertRaises(ValueError):git_actions.push_plan(self.repo)
        remote=Path(self.temp.name)/'remote.git';git(self.temp.name,'init','-q','--bare',str(remote))
        git(self.repo,'remote','add','origin',str(remote))
        arguments,branch,destination,_=git_actions.push_plan(self.repo)
        self.assertEqual((arguments,branch),(['push','--set-upstream','origin','HEAD'],'main'))
        git(self.repo,'push','-q','-u','origin','main')
        (self.repo/'b.txt').write_text('b');git(self.repo,'add','.');git(self.repo,'commit','-qm','two')
        arguments,_,destination,ahead=git_actions.push_plan(self.repo)
        self.assertEqual((arguments,destination,ahead),(['push'],'origin/main','1'))

    def test_branch_names_are_validated_by_git(self):
        self.assertEqual(git_actions.valid_branch(self.repo,'feature/x'),'feature/x')
        for bad in ('','-f','a..b','bad name','x.lock'):
            self.assertIsNone(git_actions.valid_branch(self.repo,bad),bad)
        git(self.repo,'branch','other')
        self.assertEqual(git_actions.local_branches(self.repo),['main','other'])

    def test_non_repository_project_is_refused(self):
        plain=Path(self.temp.name)/'plain';plain.mkdir();save_settings({'project':str(plain)})
        with patch('aidev.git_actions.git_read',return_value={'ok':False,'output':''}):
            with self.assertRaises(ValueError):git_actions.project()


class TaskKindTests(unittest.TestCase):
    def rows(self,*names):
        result=[]
        for name in names:
            if name.startswith('make '):result.append({'name':name,'arguments':[name[5:]]})
            elif name.startswith('Python'):result.append({'name':name,'arguments':['-m','pytest']})
            else:result.append({'name':'npm run '+name,'arguments':['run',name]})
        return result

    def test_exact_script_wins_then_prefix_then_nothing(self):
        rows=self.rows('test:unit','test','build:prod','lint')
        self.assertEqual(project_tasks.task_for_kind('test',rows)['name'],'npm run test')
        self.assertEqual(project_tasks.task_for_kind('build',rows)['name'],'npm run build:prod')
        self.assertIsNone(project_tasks.task_for_kind('format',rows))
        self.assertEqual(project_tasks.task_for_kind('test',self.rows('Python: pytest'))['name'],'Python: pytest')
        self.assertEqual(project_tasks.task_for_kind('dev',self.rows('make serve'))['name'],'make serve')
        with self.assertRaises(ValueError):project_tasks.task_for_kind('deploy',rows)

    def test_missing_kind_opens_the_explicit_task_list(self):
        with patch('aidev.project_tasks.tasks',return_value=self.rows('lint')), patch('aidev.project_tasks.launch') as launch, \
             patch('aidev.project_tasks.task_dialog') as dialog:
            project_tasks.launch_kind('test')
            launch.assert_not_called();dialog.assert_called_once_with(notice='test')
            project_tasks.launch_kind('lint')
            launch.assert_called_once()


class CommandLineTests(unittest.TestCase):
    def test_workflow_task_and_git_arguments_are_routed(self):
        from aidev.__main__ import main
        with patch('sys.argv',['ai-dev','--git','fetch']), patch('aidev.migration.migrate_legacy'), patch('aidev.git_actions.run') as run:
            main();run.assert_called_once_with('fetch')
        with patch('sys.argv',['ai-dev','--task-kind','test']), patch('aidev.migration.migrate_legacy'), patch('aidev.project_tasks.launch_kind') as run:
            main();run.assert_called_once_with('test')
        import importlib.util
        if importlib.util.find_spec('tkinter') is None:return
        with patch('sys.argv',['ai-dev','--action','mission','--workflow','review']), patch('aidev.migration.migrate_legacy'), \
             patch('aidev.ui.Panel') as panel:
            main();panel.assert_called_once_with(None,initial_workflow='review')


if __name__=='__main__':unittest.main()
