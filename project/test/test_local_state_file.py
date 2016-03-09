import codecs
import os

import pytest

from project.internal.test.tmpfile_utils import with_directory_contents
from project.local_state_file import (LocalStateFile, LOCAL_STATE_DIRECTORY, DEFAULT_RELATIVE_LOCAL_STATE_PATH,
                                      SERVICE_RUN_STATES_SECTION, possible_local_state_file_names)


def test_create_missing_local_state_file():
    def create_file(dirname):
        filename = os.path.join(dirname, DEFAULT_RELATIVE_LOCAL_STATE_PATH)
        assert not os.path.exists(filename)
        local_state_file = LocalStateFile.load_for_directory(dirname)
        assert local_state_file is not None
        assert not os.path.exists(filename)
        local_state_file.save()
        assert os.path.exists(filename)
        with codecs.open(filename, 'r', 'utf-8') as file:
            contents = file.read()
            # this is sort of annoying that the default empty file
            # has {} in it, but in our real usage we should only
            # save the file if we set something in it probably.
            assert "# Anaconda local project state\n{}\n" == contents

    with_directory_contents(dict(), create_file)


def _use_existing_local_state_file(relative_name):
    def check_file(dirname):
        filename = os.path.join(dirname, relative_name)
        assert os.path.exists(filename)
        local_state_file = LocalStateFile.load_for_directory(dirname)
        state = local_state_file.get_service_run_state("foobar")
        assert dict(port=42, shutdown_commands=[["foo"]]) == state

    sample_run_states = SERVICE_RUN_STATES_SECTION + ":\n  foobar: { port: 42, shutdown_commands: [[\"foo\"]] }\n"
    with_directory_contents({relative_name: sample_run_states}, check_file)


def test_use_existing_local_state_file_default_name():
    _use_existing_local_state_file(DEFAULT_RELATIVE_LOCAL_STATE_PATH)


def test_use_existing_local_state_file_all_names():
    for name in possible_local_state_file_names:
        _use_existing_local_state_file(os.path.join(LOCAL_STATE_DIRECTORY, name))


def test_use_empty_existing_local_state_file():
    def check_file(dirname):
        filename = os.path.join(dirname, DEFAULT_RELATIVE_LOCAL_STATE_PATH)
        assert os.path.exists(filename)
        local_state_file = LocalStateFile.load_for_directory(dirname)
        state = local_state_file.get_service_run_state("foobar")
        assert dict() == state

    with_directory_contents({DEFAULT_RELATIVE_LOCAL_STATE_PATH: ""}, check_file)


def test_modify_run_state():
    def check_file(dirname):
        filename = os.path.join(dirname, DEFAULT_RELATIVE_LOCAL_STATE_PATH)
        assert os.path.exists(filename)
        local_state_file = LocalStateFile.load_for_directory(dirname)
        state = local_state_file.get_service_run_state("foobar")
        assert dict(port=42, shutdown_commands=[["foo"]]) == state
        local_state_file.set_service_run_state("foobar", dict(port=43, shutdown_commands=[]))
        local_state_file.save()
        changed = local_state_file.get_service_run_state("foobar")
        assert dict(port=43, shutdown_commands=[]) == changed

        # and we can reload it from scratch
        local_state_file2 = LocalStateFile.load_for_directory(dirname)
        changed2 = local_state_file2.get_service_run_state("foobar")
        assert dict(port=43, shutdown_commands=[]) == changed2

    sample_run_states = SERVICE_RUN_STATES_SECTION + ":\n  foobar: { port: 42, shutdown_commands: [[\"foo\"]] }\n"
    with_directory_contents({DEFAULT_RELATIVE_LOCAL_STATE_PATH: sample_run_states}, check_file)


def test_get_all_run_states():
    def check_file(dirname):
        filename = os.path.join(dirname, DEFAULT_RELATIVE_LOCAL_STATE_PATH)
        assert os.path.exists(filename)
        local_state_file = LocalStateFile.load_for_directory(dirname)
        state = local_state_file.get_service_run_state("foo")
        assert dict(port=42) == state
        state = local_state_file.get_service_run_state("bar")
        assert dict(port=43) == state
        states = local_state_file.get_all_service_run_states()
        assert dict(foo=dict(port=42), bar=dict(port=43)) == states

    sample_run_states = SERVICE_RUN_STATES_SECTION + ":\n  foo: { port: 42 }\n  bar: { port: 43 }\n"
    with_directory_contents({DEFAULT_RELATIVE_LOCAL_STATE_PATH: sample_run_states}, check_file)


def test_run_state_must_be_dict():
    def check_cannot_use_non_dict(dirname):
        local_state_file = LocalStateFile.load_for_directory(dirname)
        with pytest.raises(ValueError) as excinfo:
            local_state_file.set_service_run_state("foo", 42)
        assert "service state should be a dict" in repr(excinfo.value)

    with_directory_contents(dict(), check_cannot_use_non_dict)
