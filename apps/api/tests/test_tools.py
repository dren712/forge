import pytest
import tempfile
import shutil
from pathlib import Path

from app.tools.repository import RepositoryTool
from app.tools.file_editor import FileEditorTool
from app.tools.shell import ShellTool
from app.tools.search import SearchTool
from app.tools.test_runner import TestRunnerTool


@pytest.fixture
def workspace():
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.mark.asyncio
async def test_file_editor_and_repository(workspace):
    editor = FileEditorTool()
    repo = RepositoryTool()

    # Create file
    create_res = await editor.execute(
        {"action": "create", "path": "src/hello.py", "content": "print('hello world')\n"},
        workspace,
    )
    assert create_res.success is True
    assert (workspace / "src" / "hello.py").exists()

    # List files via repository
    list_res = await repo.execute({"action": "list_files", "path": "."}, workspace)
    assert list_res.success is True
    assert "src/hello.py" in list_res.output

    # Read file via repository
    read_res = await repo.execute({"action": "read_file", "path": "src/hello.py"}, workspace)
    assert read_res.success is True
    assert "print('hello world')" in read_res.output

    # Patch file
    patch_res = await editor.execute(
        {"action": "patch", "path": "src/hello.py", "target": "world", "content": "FORGE"},
        workspace,
    )
    assert patch_res.success is True
    assert "print('hello FORGE')" in (workspace / "src" / "hello.py").read_text()


@pytest.mark.asyncio
async def test_security_path_traversal(workspace):
    editor = FileEditorTool()
    res = await editor.execute(
        {"action": "create", "path": "../../../outside.txt", "content": "malicious"},
        workspace,
    )
    assert res.success is False
    assert "Security violation" in (res.error or "")


@pytest.mark.asyncio
async def test_shell_tool(workspace):
    shell = ShellTool()
    res = await shell.execute({"command": "echo 'FORGE_TEST'"}, workspace)
    assert res.success is True
    assert "FORGE_TEST" in res.output


@pytest.mark.asyncio
async def test_search_tool(workspace):
    editor = FileEditorTool()
    search = SearchTool()

    await editor.execute(
        {"action": "create", "path": "lib/math.py", "content": "def calculate_mean(): return 42\n"},
        workspace,
    )
    res = await search.execute({"query": "calculate_mean"}, workspace)
    assert res.success is True
    assert "lib/math.py" in res.output
