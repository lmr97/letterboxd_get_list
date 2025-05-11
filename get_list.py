"""
This gets the elements of a list on Letterboxd
"""

from sys import argv
from shutil import get_terminal_size
from math import ceil
from datetime import datetime
from argparse import ArgumentParser
import letterboxd_list as lbl


# Superset of lbl.TABBED_ATTRS list in lbl.LetterboxdFilm.py
VALID_ATTRS = []
with open("./valid-lb-attrs.txt", "r", encoding="utf-8") as attr_file:
    VALID_ATTRS = attr_file.readlines()

VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]


def print_progress_bar(rows_now: int, total_rows: int, func_start_time: datetime):
    """
    Handles progress bar output. Wi
    """
    output_width  = get_terminal_size(fallback=(80,25))[0]-37    # runs every call to adjust to terminal changes
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
            words    = attr.split("-")
            uc_words = " ".join([w.capitalize() for w in words])
            header  += "," + uc_words

        if lb_list.is_ranked:
            header = "Rank," + header

        lbfile_writer.write(header+"\n")

        list_rank     = 1       # in case needed
        lines_written = 0
        for url in lb_list:

            film = lbl.LetterboxdFilm(url)

            title = "\"" + film.title + "\""            # rudimentary sanitizing
            file_row = title+","+film.year

            file_row += film.get_attrs_csv(attrs)

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
    url = [a for a in argv if a.startswith("http")][0]
    return url.split("/")[-2]+".csv"   # use the list name in URL .csv


def parse_cli_args() -> dict:
    """
    Parses the arguments from the command line, returning a `dict` of the results.
    """
    arg_parser = ArgumentParser(description="Collects requested film attributes from a \
        given Letterboxd list, and puts it in a CSV file (title and year are automatically \
        included, and rank if list is ranked)")

    arg_parser.add_argument('-u','--list-url',
                            type=str,
                            required=True,
                            help="The URL of the Letterboxd list."
                            )

    arg_parser.add_argument('-a','--attributes',
                            nargs='*',
                            choices=VALID_ATTRS,
                            default=[],
                            required=False,
                            help="The information about the film you'd like to add \
                                to the CSV. You can add as many attributes as you \
                                like from the list above, separated by spaces, or \
                                none at all. If none are given, only titles and years \
                                (and list rank, if applicable) are collected for the films."
                            )

    arg_parser.add_argument('-o', '--output-file',
                            type=str,
                            default=default_output_file(),
                            required=False,
                            help="CSV file to write the data to. Defaults to the \
                                list name as it appears at the end of the URL with \
                                '.csv' at the end, in the present directory."
                            )

    return vars(arg_parser.parse_args())


def main():
    """
    The main function.
    """
    cli_args = parse_cli_args()

    try:
        get_list_with_attrs(cli_args['list_url'],    # sends first argument as a list
                            cli_args['attributes'],
                            cli_args['output_file'])
        print("\n\n\033[0;32mRetrival complete!\033[0m\n")
    except lbl.RequestError as rqe:
        print(f"There is an issue with the input of your request: {repr(rqe)}")
    except lbl.HTTPError as hpe:
        print(f"Network issue during runtime: {repr(hpe)}")
    #except Exception as e:
    #    print(f"Runtime error: {repr(e)}")
    #    print("If you're seeing this, please submit an issue on GitHub.")


if __name__ == "__main__":
    main()
