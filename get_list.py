# This gets the elements of a list on Letterboxd

from sys import argv
from shutil import get_terminal_size
from math import ceil
import re
from datetime import datetime
from argparse import ArgumentParser
from pycurl import Curl
from LetterboxdFilm import LetterboxdFilm, TABBED_ATTRS, RequestError, HTTPError
from selectolax.parser import HTMLParser


# Superset of TABBED_ATTRS list in letterboxdFilm.py
VALID_ATTRS = []
with open("./valid-lb-attrs.txt", "r") as attr_file:
    VALID_ATTRS = attr_file.readlines()

VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]

def print_progress_bar(rows_now: int, total_rows: int, func_start_time: datetime):
    output_width  = get_terminal_size(fallback=(80,25))[0]-37    # runs every call to adjust as terminal changes
    completion    = rows_now/total_rows
    bar_width_now = ceil(output_width * completion)

    since_start   = datetime.now() - func_start_time
    est_remaining = since_start * (total_rows/rows_now - 1)
    minutes       = int(est_remaining.total_seconds()) // 60
    seconds       = est_remaining.seconds % 60                   # `seconds` attribute can have value > 60

    print("| ", "█" * bar_width_now, 
            (output_width - bar_width_now) * " ", "|", 
            f"{completion:.0%}  ",
            f"Time remaining: {minutes:02d}:{seconds:02d}",
            end = "\r")


def get_list_len(html_dom: HTMLParser) -> int:
    """
    Finds exact list length from first page's HTML.

    It works by using a description <meta> element in the HTML header 
    that follows the form "A list of <number> films compiled on
    Letterboxd, including <film>..." etc. (The user-made description of the 
    list comes after this standard-issue desc., after "About this list:").
    """

    # the first element is the one we want
    descr_el  = html_dom.css("meta[name='description']")[0]
    list_desc = descr_el.attributes['content']

    # get first number in the descr. str (which is list length),
    # using a regex search
    number_re = re.compile("[0-9]+")
    len_match = re.search(number_re, list_desc)         # gets first match
    list_len  = int(len_match[0])                       # cast to int for transmission

    return list_len


def get_list_with_attrs(letterboxd_list_url: str,
                        attrs: list,
                        output_file: str):
    
    print() # to give the loading bar some room to breathe
    
    list_file = []
    unretrieved_attrs = []

    curl = Curl()
    curl.setopt(curl.HTTPHEADER, ["User-Agent: Application", "Connection: Keep-Alive"])

    start_time = datetime.now()     # to use for estimation of time remaining in print_progress_bar()

    with open(output_file, "w") as lbfile_writer:

        # get number of pages
        curl.setopt(curl.URL, letterboxd_list_url)
        listpage       = curl.perform_rs()

        # check URL validity
        if (curl.getinfo(curl.HTTP_CODE) != 200):
            raise RequestError("Invalid URL; please check the URL entered and try again.")
        
        tree           = HTMLParser(listpage)
        list_len       = get_list_len(tree)
        page_num_nodes = tree.css("li.paginate-page")           # finds all page number nodes
        num_pages      = max(1, len(page_num_nodes))            # guarantee num_pages is at least 1
        list_is_ranked = bool(tree.css("p.list-number"))        # casts empty list of rank number nodes to False
        list_rank      = 1                                      # defining if needed

        for current_page in range(1, num_pages+1):              # start at 1, and include num_pages in iteration
            
            # use HTML from the GET that helps initialize page_num,
            # if on first iteration
            if (current_page > 1):
                curl.setopt(curl.URL, letterboxd_list_url+"page/"+str(current_page)+"/")
                listpage = curl.perform_rs()
                tree = HTMLParser(listpage)

            film_urls = ["https://letterboxd.com" + el.attrs['data-target-link']  for el in tree.css("div[data-target-link^='/film/']")]

            for url in film_urls:

                film = LetterboxdFilm(url, curl)

                title = "\"" + film.title + "\""            # rudimentary sanitizing
                file_row = title+","+film.year

                for attr in attrs:

                    found_attr = "(not found)"              # default
                    if   (attr in TABBED_ATTRS):
                        found_attr = film.get_tabbed_attribute(attr)
                    else:
                        match attr:
                            case "avg-rating":  found_attr = film.get_avg_rating()
                            case "casting":     found_attr = film.get_casting()
                            case "likes":       found_attr = film.get_likes()
                            case "watches":     found_attr = film.get_watches()
                            
                    
                    # convert list or dict to CSV-friendly format
                    if   (isinstance(found_attr, list)):
                        
                        found_attr = "; ".join(found_attr)  # separate list elements by ";", not "," 
                        file_row  += "," + found_attr

                    elif (isinstance(found_attr, dict)):

                        found_attr = [f"{key}: {value}" for (key, value) in found_attr.items()]
                        found_attr = "; ".join(found_attr)
                        file_row  += "," + found_attr

                    else:
                        file_row  += "," + str(found_attr)

                if (list_is_ranked):
                    file_row = str(list_rank) + "," + file_row
                    list_rank += 1

                file_row += "\n"
                list_file.append(file_row)

                print_progress_bar(len(list_file), list_len, start_time)


            if (current_page == num_pages):
                break

            current_page += 1
        

        # finalize header
        header = "Title,Year"
        for attr in attrs:
            words    = attr.split("-")
            uc_words = " ".join([w.capitalize() for w in words])
            header  += "," + uc_words   
        
        if (list_is_ranked):
            header = "Rank," + header

        header += "\n"
        list_file.insert(0, header)
        lbfile_writer.writelines(list_file)


# so the argparser will play nice with -h
def defaultOutputFile():
    if (len(argv) == 3):
        return argv[2].split("/")[-2]+".csv"   # use the list name in URL .csv
    else: 
        return argv[-1]


def parse_CLI_args():
    arg_parser = ArgumentParser(description="Collects requested film attributes from a given Letterboxd list, and puts it in a CSV file (title and year are automatically included, and rank if list is ranked)")

    arg_parser.add_argument('-u','--list-url', 
                            nargs=1, 
                            type=str, 
                            required=True, 
                            help="The URL of the Letterboxd list."
                            )
    
    arg_parser.add_argument('-a','--attributes', 
                            nargs='*', 
                            choices=VALID_ATTRS, 
                            default=[],
                            required=False, 
                            help="The information about the film you'd like to add to the CSV. You can add as many attributes as you like from the list above, separated by spaces, or none at all. If none are given, only titles and years (and list rank, if applicable) are collected for the films."
                            )
    
    arg_parser.add_argument('-o', '--output-file',
                            nargs=1, 
                            type=str, 
                            default=defaultOutputFile(), 
                            required=False,
                            help="CSV file to write the data to. Defaults to the list name as it appears at the end of the URL with '.csv' at the end, in the present directory."
                            )
    
    return vars(arg_parser.parse_args())


def main():
    cli_args = parse_CLI_args()

    try:
        get_list_with_attrs(cli_args['list_url'][0],    # sends first argument as a list
                            cli_args['attributes'],
                            cli_args['output_file'][0])
        print("\n\n\033[0;32mRetrival complete!\033[0m\n")
    except RequestError as rqe:
        print(f"There is an issue with the input of your request: {repr(rqe)}")
    except HTTPError as hpe:
        print(f"Network issue during runtime: {repr(hpe)}")
    except Exception as e:
        print(f"Runtime error: {repr(e)}")
        print("If you're seeing this, please submit an issue on GitHub.")


if (__name__ == "__main__"):
    main()
