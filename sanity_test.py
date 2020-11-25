#!/usr/bin/env python3
"""This file looks at all the directories and files available in the repository.
Then it runs them and makes sure no error occurs. We want to make sure that even when
dealii, dealfem, and python_scripts evolve over time, all of our beloved simulations
can be run and reproduced.
"""

import collections
import enum
import logging
import os
from pathlib import Path
import subprocess
import tempfile
from typing import Optional, Sequence


# setting the logs
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger.addHandler(stream_handler)


def find_shebang_executable(path: Path) -> Optional[str]:
    """Reads the first line of a file and if it has a #!, it finds the corresponding
    executable to run the program"""
    with open(str(path), 'r') as f:
        first_line = f.readline()
    if first_line.startswith('#!'):
        return first_line[2:].strip().split(' ')[-1]
    else:
        return None


class RunPython:
    """This class looks for files named run.py and runs them. It can also perform
    some static analysis on the files.
    """

    glob = '**/run.py'

    class Directory(enum.Enum):
        """Encapsulated the current directory when running the simulations.
        One option is to always run the simulation where the SOURCE of the simulation is.
        the other option is to create a TEMP directory and use that to run the simulation.
        """
        SOURCE = 0
        TEMP = 1

    def __init__(self, run_inside_dir: Directory) -> None:
        """
        Args:
            run_inside_dir: Run simulation inside this type of directory (SOURCE or TEMP)
        """
        self.dir_type = run_inside_dir

    @staticmethod
    def _choose_interpreter(path: Path) -> str:
        """Given a python file, determines which python interpreter to use"""
        suggested_interpreter = find_shebang_executable(path)
        if suggested_interpreter is not None:
            assert 'python' in suggested_interpreter, \
                'Invalid python interpreter: ' + suggested_interpreter
            return suggested_interpreter
        else:
            # For now it assumes all scripts with no shebang are python3 scripts
            # TODO: remove this assumption about python3
            return 'python3'

    def test(self, path: Path, timeout: Optional[float] = None) -> bool:
        """Tests a file. If successful, it returns true.
        A timeout can be provided to limit the execution time. However, we assume that
        whenever the process times out, it is working correctly (although it is a slow
        simulation). Thus reaching timeout causes the test to succeeds. This is a little
        counter-intuitive."""
        interpreter = RunPython._choose_interpreter(path)
        if self.dir_type == self.Directory.SOURCE:
            working_dir = str(path.parent)
        else:
            assert self.dir_type == self.Directory.TEMP
            temp_dir = tempfile.TemporaryDirectory()
            working_dir = str(temp_dir)
        # Tell all simulations to run in a single core manner to help debug error messages
        additional_env = {'NPROC': '1'}
        program_env = collections.ChainMap(os.environ, additional_env)
        proc = subprocess.Popen([interpreter, path.name], env=program_env, cwd=working_dir)
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.info('%s timed out after %f seconds. We assume it is working correctly' +
                        ' but it is an expensive task.', path, timeout)
            return True
        else:
            return proc.returncode == 0
        finally:
            if self.dir_type == self.Directory.TEMP:
                temp_dir.cleanup()


class MyPy:
    """Runs mypy on the pyton file to make sure it is correct in terms of typing"""

    glob = '**/*.py'

    @staticmethod
    def test(path: Path, timeout: Optional[float] = None) -> bool:
        from mypy import api
        output, error, exitcode = api.run([str(path)])
        success = exitcode == 0
        if not success:
            logger.error('MyPy errors for %s', path)
            if output:
                logger.error(output.strip())
            if error:
                logger.error(error.strip())
        return success


def find_and_test_all(root_dir: Path, file_templates: Sequence,
                      timeout: Optional[float] = None) -> bool:
    """Run standard sanity tests on all files.

    Args:
        root_dir: Find all files that satisfy the template in this directory.
        file_tempaltes: A list of templates that we tell us how to find files an how to find
            files and how to test them.
        timeout: The maximum amount of time spent per file per test.

    Returns:
        Whether all the tests were successful.
    """
    success = True
    logger.info('Looking for files in %s.', root_dir)
    for method in file_templates:
        logger.info('Running test method %s in files %s.', method.__class__.__name__, method.glob)
        for myfile in root_dir.glob(method.glob):
            logger.info('Testing the file %s.', myfile)
            result = method.test(myfile, timeout)
            success = success and result
            if result:
                logger.info('File %s succeeded.', myfile)
            else:
                logger.error('File %s failed.', myfile)
            logger.info('=' * 80)
        logger.info('All files tested for %s', method.__class__.__name__)
        logger.info('*' * 100)
    return success
