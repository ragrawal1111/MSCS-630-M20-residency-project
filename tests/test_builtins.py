"""
tests/test_builtins.py — Unit tests for Deliverable 1 built-in commands.
Run with: python -m pytest tests/ -v
"""
import os
import sys
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from shell.builtins import BUILTINS
from shell.parser import parse


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParser:
    def test_simple_command(self):
        tokens, is_pipe, bg = parse("echo hello")
        assert tokens == ["echo", "hello"]
        assert is_pipe is False
        assert bg is False

    def test_background_flag(self):
        tokens, is_pipe, bg = parse("ls &")
        assert tokens == ["ls"]
        assert bg is True

    def test_pipe_detection(self):
        tokens, is_pipe, bg = parse("ls | grep py")
        assert is_pipe is True
        assert tokens == [["ls"], ["grep", "py"]]

    def test_empty_input(self):
        tokens, is_pipe, bg = parse("")
        assert tokens is None

    def test_quoted_string(self):
        tokens, is_pipe, bg = parse('echo "hello world"')
        assert tokens == ["echo", "hello world"]

    def test_whitespace_only(self):
        tokens, is_pipe, bg = parse("   ")
        assert tokens is None


# ---------------------------------------------------------------------------
# Built-in: pwd / cd
# ---------------------------------------------------------------------------

class TestCdPwd:
    def test_pwd_returns_cwd(self, capsys):
        BUILTINS["pwd"]([])
        captured = capsys.readouterr()
        assert os.getcwd() in captured.out

    def test_cd_to_valid_dir(self, tmp_path):
        original = os.getcwd()
        BUILTINS["cd"]([str(tmp_path)])
        assert os.getcwd() == str(tmp_path)
        os.chdir(original)

    def test_cd_nonexistent(self, capsys):
        BUILTINS["cd"](["__nonexistent_dir__"])
        captured = capsys.readouterr()
        assert "No such file or directory" in captured.out

    def test_cd_no_args_goes_home(self):
        original = os.getcwd()
        BUILTINS["cd"]([])
        assert os.getcwd() == os.path.expanduser("~")
        os.chdir(original)


# ---------------------------------------------------------------------------
# Built-in: echo
# ---------------------------------------------------------------------------

class TestEcho:
    def test_echo_words(self, capsys):
        BUILTINS["echo"](["hello", "world"])
        assert capsys.readouterr().out.strip() == "hello world"

    def test_echo_empty(self, capsys):
        BUILTINS["echo"]([])
        assert capsys.readouterr().out.strip() == ""


# ---------------------------------------------------------------------------
# Built-in: ls
# ---------------------------------------------------------------------------

class TestLs:
    def test_ls_lists_files(self, tmp_path, capsys):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()
        BUILTINS["ls"]([str(tmp_path)])
        out = capsys.readouterr().out
        assert "a.txt" in out
        assert "b.txt" in out

    def test_ls_nonexistent(self, capsys):
        BUILTINS["ls"](["__no_such_dir__"])
        assert "No such file or directory" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Built-in: touch / cat / rm
# ---------------------------------------------------------------------------

class TestFileCmds:
    def test_touch_creates_file(self, tmp_path):
        target = str(tmp_path / "new.txt")
        BUILTINS["touch"]([target])
        assert os.path.exists(target)

    def test_cat_prints_contents(self, tmp_path, capsys):
        f = tmp_path / "hello.txt"
        f.write_text("hello\n")
        BUILTINS["cat"]([str(f)])
        assert "hello" in capsys.readouterr().out

    def test_cat_missing_file(self, capsys):
        BUILTINS["cat"](["__ghost__.txt"])
        assert "No such file or directory" in capsys.readouterr().out

    def test_cat_no_args(self, capsys):
        BUILTINS["cat"]([])
        assert "missing file operand" in capsys.readouterr().out

    def test_rm_removes_file(self, tmp_path):
        f = tmp_path / "del.txt"
        f.write_text("bye")
        BUILTINS["rm"]([str(f)])
        assert not f.exists()

    def test_rm_missing_file(self, capsys):
        BUILTINS["rm"](["__no_file__.txt"])
        assert "No such file or directory" in capsys.readouterr().out

    def test_rm_no_args(self, capsys):
        BUILTINS["rm"]([])
        assert "missing operand" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Built-in: mkdir / rmdir
# ---------------------------------------------------------------------------

class TestDirCmds:
    def test_mkdir_creates_dir(self, tmp_path):
        target = str(tmp_path / "newdir")
        BUILTINS["mkdir"]([target])
        assert os.path.isdir(target)

    def test_mkdir_existing(self, tmp_path, capsys):
        BUILTINS["mkdir"]([str(tmp_path)])  # already exists
        assert "File exists" in capsys.readouterr().out

    def test_mkdir_no_args(self, capsys):
        BUILTINS["mkdir"]([])
        assert "missing operand" in capsys.readouterr().out

    def test_rmdir_removes_empty(self, tmp_path):
        d = tmp_path / "empty"
        d.mkdir()
        BUILTINS["rmdir"]([str(d)])
        assert not d.exists()

    def test_rmdir_nonempty(self, tmp_path, capsys):
        d = tmp_path / "full"
        d.mkdir()
        (d / "file.txt").touch()
        BUILTINS["rmdir"]([str(d)])
        assert d.exists()  # should NOT have been removed
        out = capsys.readouterr().out
        assert out  # some error message printed

    def test_rmdir_missing(self, capsys):
        BUILTINS["rmdir"](["__no_dir__"])
        assert "No such file or directory" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Built-in: kill
# ---------------------------------------------------------------------------

class TestKill:
    def test_kill_invalid_pid_string(self, capsys):
        BUILTINS["kill"](["abc"])
        assert "invalid pid" in capsys.readouterr().out

    def test_kill_no_args(self, capsys):
        BUILTINS["kill"]([])
        assert "usage" in capsys.readouterr().out

    def test_kill_nonexistent_pid(self, capsys):
        BUILTINS["kill"](["999999999"])
        out = capsys.readouterr().out
        # Error message varies by OS; just ensure something was printed
        assert out.startswith("shell: kill:")
