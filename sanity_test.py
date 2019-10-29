#!/usr/bin/env python3
"""This file looks at all the directories and files available in the repository.
Then it runs them and makes sure no error occurs. We want to make sure that even when
dealii, dealfem, and python_scripts evolve over time, all of our beloved simulations
can be run and reproduced.
"""

from pathlib import Path
import subprocess
import os
from typing import Optional


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

    @staticmethod
    def test(path: Path, timeout: Optional[float] = None) -> bool:
        """Tests a file. If successful, it returns true.
        A timeout can be provided to limit the execution time. However, we assume that
        whenever the process times out, it is working correctly (although it is a slow
        simulation). Thus reaching timeout causes the test to succeeds. This is a little
        counter-intuitive."""
        try:
            assert os.access(str(path), os.X_OK), '{} is not executable'.format(path)
            subprocess.run(['./' + path.name], check=True, cwd=str(path.parent), timeout=timeout)
        except subprocess.TimeoutExpired:
            return True
        except subprocess.CalledProcessError:
            return False
        else:
            return True


def find_and_test_all(path: Path, file_template, timeout: Optional[float] = None) -> None:
    """Given a file template (a class similar to RunPython) find all instances of those files"""
    for myfile in path.glob(file_template.glob):
        print('Testing the file {}'.format(myfile))
        assert file_template.test(myfile, timeout)
