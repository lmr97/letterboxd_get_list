# This gets the elements of a list on Letterboxd

from sys import argv
from shutil import get_terminal_size
from math import ceil
from datetime import datetime
from argparse import ArgumentParser
from pycurl import Curl
from LetterboxdFilm import LetterboxdFilm, TABBED_ATTRS
from selectolax.parser import HTMLParser
    

# Superset of TABBED_ATTRS list in letterboxdFilm.py
VALID_ATTRS  = ["actor",
                "additional-directing",
                "additional-photography",
                "art-direction",
                "assistant-director",
                "avg_rating",
                "camera-operator",
                "casting",
                "choreography",
                "cinematography",
                "composer",
                "costume-design",
                "country",
                "director",
                "editor",
                "executive-producer",
                "genre",
                "hairstyling",
                "language",
                "lighting",
                "likes",
                "makeup",
                "mini-theme",
                "original-writer",
                "producer",
                "production-design",
                "set-decoration",
                "songs",
                "sound",
                "special-effects",
                "special-effects",
                "studio",
                "stunts",
                "theme",
                "title-design",
                "visual-effects",
                "watches",
                "writer"
                ]

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
        tree           = HTMLParser(listpage)
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
                            case "avg_rating":  found_attr = film.get_avg_rating()
                            case "casting":     found_attr = film.get_casting()
                            case "likes":       found_attr = film.get_likes()
                            case "watches":     found_attr = film.get_watches()
                            
                    
                    # convert list or dict to CSV-friendly format
                    if   (type(found_attr) == list):
                        
                        found_attr = "; ".join(found_attr)  # separate list elements by ";", not "," 
                        file_row  += "," + found_attr

                    elif (type(found_attr) == dict):

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

                # make sure loading bar has the correct denominator
                if (len(film_urls) < 100):
                    print_progress_bar(len(list_file), 100*num_pages - (100-len(film_urls)), start_time)
                else:
                    print_progress_bar(len(list_file), len(film_urls)*num_pages, start_time)


            if (current_page == num_pages): break
            current_page += 1
        

        # finalize header
        header = "Title,Year"
        for attr in attrs:
            if (attr not in unretrieved_attrs):
                header += "," + attr.capitalize()
        
        if (list_is_ranked): header = "Rank," + header

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

    get_list_with_attrs(cli_args['list_url'][0],    # sends first argument as a list
                        cli_args['attributes'],
                        cli_args['output_file'][0])

    print("\n\n\033[0;32mRetrival complete!\033[0m\n")



if (__name__ == "__main__"):
    main()
