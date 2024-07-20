# This gets the elements of a list on Letterboxd

from sys import argv
from shutil import get_terminal_size
from math import ceil
from argparse import ArgumentParser
from fnmatch import filter
from requests import Session
from LetterboxdFilm import LetterboxdFilm
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
                "story",
                "studio",
                "stunts",
                "theme",
                "title-design",
                "visual-effects",
                "watches",
                "writer"
                ]

def print_loading_bar(rows_now, total_rows):
    output_width = get_terminal_size(fallback=(80,25))[0]-11    # runs every call to adjust as terminal changes

    bar_width_now = ceil(output_width * (rows_now)/total_rows)

    print("| ", "█" * bar_width_now, 
            (output_width - bar_width_now) * " ", "|", 
            f"{(rows_now)/total_rows:.0%}",
            end = "\r")



def get_list_with_attrs(letterboxd_list_url: str,
                        attrs: list,
                        output_file: str):
    
    print() # to give the loading bar some room to breathe
    
    list_file = []
    unretrieved_attrs = []
    user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"

    with Session() as s:
        s.headers['User-Agent'] = user_agent

        with open(output_file, "w") as lbfile_writer:
            
            num_pages = 1  # update this value later
            current_page = 1
            listwide_vars_updated = False
            list_is_ranked = False
            list_rank = 1
            while(True):
                
                listpage = s.get(letterboxd_list_url+"page/"+str(current_page)+"/")
                tree = HTMLParser(listpage.text)
                film_urls = ["https://letterboxd.com" + el.attrs['data-target-link']  for el in tree.css("div[data-target-link^='/film/']")]

                # placed in if statement so it the CSS searches don't run every iteration
                if (not listwide_vars_updated):
                    page_num_nodes = tree.css("li.paginate-page")
                    list_num_nodes = tree.css("p.list-number")
                    
                    if (page_num_nodes): 
                        num_pages = int(page_num_nodes[-1].text())
                     
                    if (list_num_nodes):
                        list_is_ranked = True
                    
                    listwide_vars_updated = True


                for url in film_urls:
  
                    film = LetterboxdFilm(url)

                    title = "\"" + film.title + "\""            # sanitizing
                    file_row = title+","+film.year


                    for attr in attrs:

                        # look through dictionary of method names for attr...
                        matches = filter(vars(LetterboxdFilm).keys(), "*"+attr)
                        
                        # ...and call the method associated with the given attr
                        if (matches): 
                            found_attr = vars(LetterboxdFilm)[matches[0]](film)
                        

                        # if it's not there, it could be a tabbed attribute, so try that
                        else:
                            try:
                                found_attr = film.get_tabbed_attribute(attr)
                            
                            # keep track of unfound attrs, for header construction
                            except (ValueError):
                                unretrieved_attrs.append(attr)
                                pass
                        
                        # convert list or dict to CSV-friendly format
                        if (   type(found_attr) == list
                            or type(found_attr) == dict):
                            
                            found_attr = str(found_attr)
                            found_attr = found_attr[2:-2]               # take off brackets
                            found_attr = found_attr.replace("\'", "")   # take out quote marks
                            found_attr = found_attr.replace(",", ";")   # separate list/dict elements by ";", not ","

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
                        print_loading_bar(len(list_file), 100*num_pages - (100-len(film_urls)))
                    else:
                        print_loading_bar(len(list_file), len(film_urls)*num_pages)


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

    arg_parser.add_argument('-l','--list-url', 
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
                        cli_args['output_file'])

    print("\n\nRetrival complete!\n")



if (__name__ == "__main__"):
    main()
