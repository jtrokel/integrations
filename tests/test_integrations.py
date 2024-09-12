"""Tests for integrations.py.
"""

import pytest

import main


def test_parser_create_1():
    args = main.build_parser(["create", "xx"])
    assert args.file == "xx"


def test_parser_create_2():
    args = main.build_parser(["create", "xx"])
    assert not args.check_config


def test_parser_create_3():
    args = main.build_parser(["create", "xx", "--out", "yy"])
    assert args.out == "yy"


def test_parser_create_4():
    args = main.build_parser(["create", "xx"])
    assert args.outfile


def test_parser_list_1():
    args = main.build_parser(["list"])
    assert args


def test_parser_delete_1():
    args = main.build_parser(["delete", "xx"])
    assert args.file == "xx"


def test_parser_delete_2():
    args = main.build_parser(["delete", "xx", "-m", "yy"])
    assert args.mapfile == "yy"


def test_parser_delete_3():
    args = main.build_parser(["delete", "xx"])
    assert (
        not args.generate_map
        and not args.check_config
        and not args.regex
        and not args.interactive
    )


def test_validate_args():
    args = main.build_parser(["create", "xx", "-o", "yy", "--no-outfile"])
    with pytest.raises(SystemExit) as wrapped_e:
        main.validate_args(args)
    assert wrapped_e.type is SystemExit
    assert wrapped_e.value.code == 1


def test_run_cmd():

