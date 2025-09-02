"""
Testing the CLI and unit testing.
"""
import sys
import pytest
from pandas import read_csv
import src.letterboxd_list.__main__ as lbmain

HELP_OUTPUT = """
"""

def test_arg_parsing_good_args():

    # I know these lines are obscenely long, but theses tests don't work when the lists
    # are defined across multiple lines, when "likes" is included.
    good_arg_combos  = {
        "long form args, with output file":  ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"],
        "short form args, with output file": ["lblist", "-u", "https://letterboxd.com/dialectica972/list/truly-random-films/", "-a", "director", "writer", "cast-list", "likes", "-o", "~/path/to/output.csv"],
        "short form args, no output file":   ["lblist", "-u", "https://letterboxd.com/dialectica972/list/truly-random-films/", "-a", "director", "writer", "cast-list", "likes"],
        "long form args, no output file":    ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes"],
        "with debug option":                 ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes", "--debug",],
        "mixed arg forms, with output file": ["lblist", "-u", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes", "-o", "~/path/to/output.csv"],
        "min required args":                 ["lblist", "-u", "https://letterboxd.com/dialectica972/list/truly-random-films/"]
    }

    correct_parsings = [
        {
            "debug": False,
            "list_url": "https://letterboxd.com/dialectica972/list/truly-random-films/",
            "attributes": ["director", "writer", "cast-list", "likes"],
            "output_file": "truly-random-films.csv"
        },
        {
            "debug": False,
            "list_url": "https://letterboxd.com/dialectica972/list/truly-random-films/",
            "attributes": ["director", "writer", "cast-list", "likes"],
            "output_file": "~/path/to/output.csv"
        },
        {
            "debug": True,
            "list_url": "https://letterboxd.com/dialectica972/list/truly-random-films/",
            "attributes": ["director", "writer", "cast-list", "likes"],
            "output_file": "truly-random-films.csv"
        },
        {
            "debug": False,
            "list_url": "https://letterboxd.com/dialectica972/list/truly-random-films/",
            "attributes": [],
            "output_file": "truly-random-films.csv"
        }
    ]

    for name, combo in good_arg_combos.items():
        sys.argv = combo
        parsing  = lbmain.parse_cli_args()

        if "~/path/to/output.csv" in combo:
            assert correct_parsings[1] == parsing, f"{name} combo failed"
        elif "--debug" in combo:
            assert correct_parsings[2] == parsing, f"{name} combo failed"
        elif "director" not in combo:
            assert correct_parsings[3] == parsing, f"{name} combo failed"
        else:
            assert correct_parsings[0] == parsing, f"{name} combo failed"

def test_arg_parsing_bad_args():
    bad_arg_combos = [
        ["lblist"],             # no args
        ["lblist", "-d"],       # arg that doesn't exist, short
        ["lblist", "--badarg"], # arg that doesn't exist, long
        # valid, except missing required arg
        ["lblist", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"],
        # valid, except missing value to --list-url
        ["lblist", "--list-url", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"],
        # same as above, but with short version and mixed arg types
        ["lblist", "-u", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"],
    ]

    for combo in bad_arg_combos:
        sys.argv = combo
        with pytest.raises(SystemExit):
            lbmain.parse_cli_args()


def test_cap_header():
    assert lbmain.to_capital_header("value") == "Value"
    assert lbmain.to_capital_header("header-with-multiple-words") == "Header With Multiple Words"


def test_gen_default_filename():

    sys.argv = ["lblist", "other", "args"]
    assert lbmain.default_output_file() is None

    sys.argv.append("https://letterboxd.com/dialectica972/list/the-american-dream/")
    assert lbmain.default_output_file() == "the-american-dream.csv"


def test_cli_value_errors(capsys):

    bad_url_args    = ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/list-no-exist/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"]
    bad_attr_args   = ["lblist", "-u", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "bingus", "likes", "--output-file", "~/path/to/output.csv"]
    dir_output_args = ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "imadir"]
    http_err_arg    = ["lblist", "-u", "https://httpbin.org/status/500", "--attributes", "director", "writer", "likes", "--output-file", "~/path/to/output.csv"]

    sys.argv = bad_url_args
    lbmain.main()
    captured = capsys.readouterr()
    assert "RequestError" in captured.err

    # since the bad attributes are caught by argparse, which calls sys.exit(2)
    # when the CLI args are invalid, we've got to catch a SystemExit
    with pytest.raises(SystemExit):
        sys.argv = bad_attr_args
        lbmain.main()

    sys.argv = dir_output_args
    lbmain.main()
    captured = capsys.readouterr()
    assert ("IsADirectoryError" in captured.err) or ("PermissionError" in captured.err)

    sys.argv = http_err_arg
    lbmain.main()
    captured = capsys.readouterr()
    assert "HTTPError" in captured.err


def test_cli_good_run():
    """
    Make sure the CLI can run without errors with maximal inputs, on a short list

    The output is checked to make sure: 
        1) it can be parsed by a good CSV reader,
        2) it contains Rank, Title, and Year headers (regardless of if attributes were specified)
        3) it contains Rank, Title, and Year values
    
    The accuracy is checked by the other unit tests for the classes, separately.
    """
    normal_val_args = ["lblist", "--list-url", "https://letterboxd.com/dialectica972/list/testing-a-ranked-list/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "./test-file.csv"]
    min_args        = ["lblist", "-u", "https://letterboxd.com/dialectica972/list/testing-a-ranked-list/"]
    
    sys.argv = normal_val_args
    lbmain.main()

    output_df = read_csv("./test-file.csv")
    assert (["Rank", "Title", "Year", "Cast List", "Director", "Likes", "Writer"] == output_df.columns).all()  # check alphabetization
    assert output_df.iat[3,0] == 4, "Rank not correct."
    assert output_df.iat[3,1] == "Godzilla Minus One", "Title not correct."
    assert output_df.iat[3,2] == 2023, "Year not correct."

    sys.argv = min_args
    lbmain.main()
    min_output = read_csv("./testing-a-ranked-list.csv")
    assert (["Rank", "Title", "Year"] == min_output.columns).all()
    assert min_output.iat[3,0] == 4, "Rank not correct."
    assert min_output.iat[3,1] == "Godzilla Minus One", "Title not correct."
    assert min_output.iat[3,2] == 2023, "Year not correct."

def test_debug_run(capsys):
    """
    This is mainly here for coverage. The CLI being able to crash hard in 
    debug mode is a part of the design, (to show the trace output) but it 
    should not crash with these arguments.

    This test is essentially the same as `test_cli_good_run()`, except with
    `--debug` in the arguments and without a bad attribute argument list.
    (checked earlier).
    """
    bad_url_args    = ["lblist", "--debug", "--list-url", "https://letterboxd.com/dialectica972/list/list-no-exist/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "~/path/to/output.csv"]
    dir_output_args = ["lblist", "--debug", "--list-url", "https://letterboxd.com/dialectica972/list/truly-random-films/", "--attributes", "director", "writer", "cast-list", "likes", "--output-file", "imadir"]
    http_err_arg    = ["lblist", "--debug", "-u", "https://httpbin.org/status/500", "--attributes", "director", "writer", "likes", "--output-file", "~/path/to/output.csv"]

    sys.argv = bad_url_args
    lbmain.main()
    captured = capsys.readouterr()
    assert "RequestError" in captured.err

    sys.argv = dir_output_args
    lbmain.main()
    captured = capsys.readouterr()
    assert ("IsADirectoryError" in captured.err) or ("PermissionError" in captured.err)

    sys.argv = http_err_arg
    lbmain.main()
    captured = capsys.readouterr()
    assert "HTTPError" in captured.err
