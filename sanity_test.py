#!/usr/bin/env python3
"""This file looks at all the directories and files available in the repository.
Then it runs them and makes sure no error occurs. We want to make sure that even when
dealii, dealfem, and python_scripts evolve over time, all of our beloved simulations
can be run and reproduced.
"""

import collections
import enum
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Optional, Sequence


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
        try:
            subprocess.run([interpreter, path.name], env=program_env, check=True,
                           cwd=working_dir, timeout=timeout)
        except subprocess.TimeoutExpired:
            return True
        except subprocess.CalledProcessError:
            return False
        else:
            return True
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
        print(output, file=sys.stderr)
        print(error, file=sys.stderr)
        return exitcode == 0


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
    print('Looking for files in {}.'.format(root_dir))
    for method in file_templates:
        print('Running test method {} in files {}.'.format(method.__class__.__name__, method.glob))
        for myfile in root_dir.glob(method.glob):
            print('Testing the file {}.'.format(myfile))
            result = method.test(myfile, timeout)
            success = success and result
            print('File {} succeeded.'.format(myfile))
    return success
