"""
This gets the elements of a list on Letterboxd
"""

import sys
from shutil import get_terminal_size
from math import ceil
from datetime import datetime
from argparse import ArgumentParser
import letterboxd_list.containers as lbl

def print_progress_bar(rows_now: int, total_rows: int, func_start_time: datetime):
    """
    Handles progress bar output. Will change width if terminal width changes
    during runtime.
    """
    output_width  = get_terminal_size(fallback=(80,25))[0]-37
    completion    = rows_now/total_rows
    bar_width_now = ceil(output_width * completion)

    since_start   = datetime.now() - func_start_time
    est_remaining = since_start * (total_rows/rows_now - 1)
    minutes       = int(est_remaining.total_seconds()) // 60
    seconds       = est_remaining.seconds % 60                   # `seconds` may be > 60

    print("| ", "█" * bar_width_now,
            (output_width - bar_width_now) * " ", "|",
            f"{completion:.0%}  ",
            f"Time remaining: {minutes:02d}:{seconds:02d}",
            end = "\r")


def to_capital_header(attr: str) -> str:
    """
    Capitalizes the first word in a given string,
    and replaces the `-` with a space.
    """
    words    = attr.split("-")
    init_cap = [w.capitalize() for w in words]
    uc_attr  = " ".join(init_cap)
    return uc_attr


def get_list_with_attrs(letterboxd_list_url: str,
                        attrs: list,
                        output_file: str):
    """
    The central function for the app.
    """

    print()                         # to give the loading bar some room to breathe
    start_time = datetime.now()     # used in est time remaining in print_progress_bar()
    lb_list    = lbl.LetterboxdList(letterboxd_list_url)

    with open(output_file, "w", encoding="utf-8") as lbfile_writer:

        # finalize header
        header = "Title,Year"
        for attr in attrs:
            header  += "," + to_capital_header(attr)

        if lb_list.is_ranked:
            header = "Rank," + header

        lbfile_writer.write(header+"\n")

        list_rank     = 1       # in case needed
        lines_written = 0
        for url in lb_list:

            film = lbl.LetterboxdFilm(url)

            title = "\"" + film.title + "\""            # rudimentary sanitizing
            file_row = title+","+film.year

            if len(attrs) > 0:
                file_row += "," + film.get_attrs_csv(attrs)

            if lb_list.is_ranked:
                file_row = str(list_rank) + "," + file_row
                list_rank += 1

            file_row += "\n"

            lbfile_writer.write(file_row)

            lines_written += 1
            print_progress_bar(lines_written, lb_list.length, start_time)


# so the argparser will play nice with -h
def default_output_file():
    """
    Generate default output file name.
    """
    url = [a for a in sys.argv if a.startswith("http")]

    if len(url) == 0:
        return None

    return url[0].split("/")[-2]+".csv"   # use the list name in URL .csv


def parse_cli_args() -> dict:
    """
    Parses the arguments from the command line, returning a `dict` of the results.
    """
    ap = ArgumentParser(description="Collects requested film attributes from a \
        given Letterboxd list, and puts it in a CSV file (title and year are automatically \
        included, and rank if list is ranked)")

    ap.add_argument('-u','--list-url',
                    type=str,
                    required=True,
                    help="The URL of the Letterboxd list."
                    )

    ap.add_argument('-a','--attributes',
                    nargs='*',
                    choices=lbl.VALID_ATTRS,
                    default=[],
                    required=False,
                    help="The information about the film you'd like to add \
                        to the CSV. You can add as many attributes as you \
                        like from the list above, separated by spaces, or \
                        none at all. If none are given, only titles and years \
                        (and list rank, if applicable) are collected for the films."
                    )

    ap.add_argument('-o', '--output-file',
                    type=str,
                    default=default_output_file(),
                    required=False,
                    help="CSV file to write the data to. Defaults to the \
                        list name as it appears at the end of the URL with \
                        '.csv' at the end, in the present directory."
                    )

    ap.add_argument('--debug',
                    default=False,
                    action='store_true',
                    required=False,
                    help="This option lets the program crash fully, so a stack \
                        trace will be printed to the console."
                    )


    return vars(ap.parse_args())


def main():
    """
    The main function.
    """
    cli_args = parse_cli_args()

    # a fairly rudimental "debug mode", I know
    if cli_args['debug']:
        print("\033[0;33m  /// Running in debug mode /// \033[0m")
        try:
            get_list_with_attrs(cli_args['list_url'],    # sends first argument as a list
                                cli_args['attributes'],
                                cli_args['output_file'])
            print("\n\n\033[0;32mRetrival complete!\033[0m\n")
        except lbl.RequestError as rqe:
            print(f"There is an issue with the input of your request: {repr(rqe)}", file=sys.stderr)
        except lbl.HTTPError as hpe:
            print(f"Network issue during runtime: {repr(hpe)}", file=sys.stderr)
        except IsADirectoryError as iade:
            print("The output file you've given is actually a directory within the current ",
            f"working directory. Try again with another name!\nFull error: {repr(iade)}", file=sys.stderr)
        except PermissionError as pe:
            print("It looks like you don't have permission to access the output file you want to ",
            "write to. If you're on Windows, your OS may have raised this error because the ",
            "output filename you chose is the name of a directory in the current working ",
            f"directory.\nFull error: {repr(pe)}", file=sys.stderr)
    else:
        try:
            get_list_with_attrs(cli_args['list_url'],    # sends first argument as a list
                                cli_args['attributes'],
                                cli_args['output_file'])
            print("\n\n\033[0;32mRetrival complete!\033[0m\n")
        except lbl.RequestError as rqe:
            print(f"There is an issue with the input of your request: {repr(rqe)}", file=sys.stderr)
        except lbl.HTTPError as hpe:
            print(f"Network issue during runtime: {repr(hpe)}", file=sys.stderr)
        except IsADirectoryError as iade:
            print("The output file you've given is actually a directory within the current ",
            f"working directory. Try another name!\nFull error: {repr(iade)}", file=sys.stderr)
        except PermissionError as pe:
            print("It looks like you don't have permission to access the output file you want to ",
            "write to. If you're on Windows, your OS may have raised this error because the ",
            "output filename you chose is the name of a directory in the current working ",
            f"directory.\nFull error: {repr(pe)}", file=sys.stderr)
        except Exception as e:
            print(f"Runtime error: {repr(e)}", file=sys.stderr)
            print("If you're seeing this, please re-run the command you just ran ",
                "with the `--debug` flag, and submit an issue on GitHub with the debug output.", 
                file=sys.stderr)
