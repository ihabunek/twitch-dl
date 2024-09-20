import asyncio
import hashlib
import os
import tempfile
from pathlib import Path
from typing import NamedTuple

import pytest
from pytest_httpserver import HTTPServer

from twitchdl.http import TaskError, TaskSuccess, download_all

MiB = 1024**2


class File(NamedTuple):
    data: bytes
    hash: str
    path: str


def generate_test_file(size: int):
    data = os.urandom(size)
    hash = hashlib.sha256(data).hexdigest()
    return File(data, hash, f"/{hash}")


def hash_file(path: Path):
    hash = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read()
            if not chunk:
                break
            hash.update(chunk)
    return hash.hexdigest()


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_success(httpserver: HTTPServer, temp_dir: Path):
    count = 10
    workers = 5
    file_size = 1 * MiB

    files = [generate_test_file(file_size) for _ in range(count)]
    for f in files:
        httpserver.expect_request(f.path).respond_with_data(f.data)  # type: ignore

    sources = [httpserver.url_for(f.path) for f in files]
    targets = [temp_dir / f.hash for f in files]

    result = asyncio.run(download_all(zip(sources, targets), workers))
    assert result.ok
    assert len(result.results) == count

    for index, (file, source, target, result) in enumerate(
        zip(files, sources, targets, result.results)
    ):
        assert isinstance(result, TaskSuccess)
        assert result.ok
        assert not result.existing
        assert result.task_id == index
        assert result.size == file_size
        assert result.url == source
        assert result.target == target

        assert target.exists()
        assert os.path.getsize(target) == file_size
        assert file.hash == hash_file(target)


def test_allow_failures(httpserver: HTTPServer, temp_dir: Path):
    count = 10
    workers = 5
    file_size = 1 * MiB
    failing_index = 5

    files = [generate_test_file(file_size) for _ in range(count)]
    for index, f in enumerate(files):
        if index == failing_index:
            httpserver.expect_request(f.path).respond_with_data("not found", status=404)  # type: ignore
        else:
            httpserver.expect_request(f.path).respond_with_data(f.data)  # type: ignore

    sources = [httpserver.url_for(f.path) for f in files]
    targets = [temp_dir / f.hash for f in files]

    result = asyncio.run(download_all(zip(sources, targets), workers))
    results = result.results
    assert result.ok
    assert len(results) == count

    for index, (file, source, target, result) in enumerate(zip(files, sources, targets, results)):
        if index == failing_index:
            assert not target.exists()
            assert isinstance(result, TaskError)
            assert result.task_id == index
            assert not result.ok
            assert result.url == source
            assert result.target == target
        else:
            assert target.exists()
            assert os.path.getsize(target) == file_size
            assert file.hash == hash_file(target)
            assert isinstance(result, TaskSuccess)
            assert result.task_id == index
            assert result.size == file_size
            assert not result.existing
            assert result.ok
            assert result.url == source
            assert result.target == target


def test_dont_allow_failures(httpserver: HTTPServer, temp_dir: Path):
    count = 10
    workers = 5
    file_size = 1 * MiB
    failing_index = 5

    files = [generate_test_file(file_size) for _ in range(count)]
    for index, f in enumerate(files):
        if index == failing_index:
            httpserver.expect_request(f.path).respond_with_data("not found", status=404)  # type: ignore
        else:
            httpserver.expect_request(f.path).respond_with_data(f.data)  # type: ignore

    sources = [httpserver.url_for(f.path) for f in files]
    targets = [temp_dir / f.hash for f in files]

    result = asyncio.run(download_all(zip(sources, targets), workers, allow_failures=False))
    results = result.results
    assert not result.ok
    assert len(results) == count

    for index, (file, source, target, result) in enumerate(zip(files, sources, targets, results)):
        if index == failing_index:
            assert not target.exists()
            assert isinstance(result, TaskError)
            assert result.task_id == index
            assert not result.ok
            assert result.url == source
            assert result.target == target
        else:
            assert target.exists()
            assert os.path.getsize(target) == file_size
            assert file.hash == hash_file(target)
            assert isinstance(result, TaskSuccess)
            assert result.task_id == index
            assert result.size == file_size
            assert not result.existing
            assert result.ok
            assert result.url == source
            assert result.target == target
