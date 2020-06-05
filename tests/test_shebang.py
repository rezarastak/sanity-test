from pathlib import Path

import sanity_test


def test_find_shebang_executable(tmp_path: Path) -> None:
    myfile = tmp_path / 'sample.txt'
    myfile.write_text("""#!/usr/bin/mybin

Some code
Some more code
""")
    result = sanity_test.find_shebang_executable(myfile)
    assert result == '/usr/bin/mybin'
