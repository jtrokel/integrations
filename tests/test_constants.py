"""Tests for constants.py.
"""
import os

import pytest

import constants

def test_create_const():
    assert constants.CREATE == "create"

def test_list_const():
    assert constants.LIST == "list"

def test_delete_const():
    assert constants.DELETE == "delete"

def test_update_const():
    assert constants.UPDATE == "update"

def test_root_dir(monkeypatch):
    monkeypatch.chdir("../src")
    this_dir = os.getcwd()
    assert this_dir == constants.ROOT_DIR
