# The server translates HTTP GET request query into JSON bytes,
# and sends them here. since this program is not directly
# # accessible to the network, it only uses the data format
# I will give it from the server, and send back text as a
# # CSV stream of text, with each line delimited by LF (not CRLF).
# Error handling and bundling the data as an HTTP response
# is also done at the server.
#
# The model is as follows:
#
#                  CSV text <- (here)
#                      |         ^
#                      v         |
#   Client HTTP <--> Server -> JSON
# 
# simple as.

import json
import socket
from pycurl import Curl
from selectolax.parser import HTMLParser
from LetterboxdFilm import LetterboxdFilm, TABBED_ATTRS
    

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



def get_film_num_est():
    return


def get_list_with_attrs(list_path: str, attrs: list) -> list:
    """Gets the requested attributed from the films on a Letterboxd list."""
    list_file = []
    unretrieved_attrs = []

    curl = Curl()
    curl.setopt(curl.HTTPHEADER, ["User-Agent: Application", "Connection: Keep-Alive"])
    lb_list_url = "https://letterboxd.com/" + list_path
    
    # get number of pages
    curl.setopt(curl.URL, lb_list_url)
    listpage       = curl.perform_rs()
    tree           = HTMLParser(listpage)
    page_num_nodes = tree.css("li.paginate-page")     # finds all page number nodes
    num_pages      = max(1, len(page_num_nodes))      # guarantee num_pages is at least 1
    list_is_ranked = bool(tree.css("p.list-number"))  # casts empty list of nodes to False
    list_rank      = 1                                # defining if needed

    for current_page in range(1, num_pages+1):        # start at 1, including num_pages in iteration

        # use HTML from the GET that helps initialize page_num,
        # if on first iteration
        if (current_page > 1):
            curl.setopt(curl.URL, lb_list_url+"page/"+str(current_page)+"/")
            listpage = curl.perform_rs()
            tree = HTMLParser(listpage)

        # a list comprehension, if you can believe it
        film_urls = [
            "https://letterboxd.com" + el.attrs['data-target-link']
            for el in tree.css("div[data-target-link^='/film/']")
        ]

        for url in film_urls:

            film = LetterboxdFilm(url, curl)

            title = "\"" + film.title + "\""            # rudimentary sanitizing
            file_row = title+","+film.year

            for attr in attrs:

                found_attr = "(not found)"              # default
                if (attr in TABBED_ATTRS):
                    found_attr = film.get_tabbed_attribute(attr)
                else:
                    match attr:
                        case "avg_rating":  found_attr = film.get_avg_rating()
                        case "casting":
                            found_attr = film.get_casting()
                            found_attr = [
                                f"{key}: {value}" for (key, value) in found_attr.items()
                            ]
                            found_attr = "; ".join(found_attr)
                            file_row  += "," + found_attr
                        case "likes":       found_attr = film.get_likes()
                        case "watches":     found_attr = film.get_watches()

                # convert list or dict to CSV-friendly format
                if (isinstance(found_attr, list)):
                    found_attr = "; ".join(found_attr)  # separate list elements by ";", not "," 
                    file_row  += "," + found_attr
                else:
                    file_row  += "," + str(found_attr)

            if (list_is_ranked):
                file_row = str(list_rank) + "," + file_row
                list_rank += 1

            file_row += "\n"
            list_file.append(file_row)

        if (current_page == num_pages):
            break

        current_page += 1


    # finalize header
    header = "Title,Year"
    for attr in attrs:
        if (attr not in unretrieved_attrs):
            header += "," + attr.capitalize()

    if (list_is_ranked):
        header = "Rank," + header

    header += "\n"
    list_file.insert(0, header)

    return list_file


def send_csv(conn: socket.socket, list_data: list):
    """This function sends only the CSV content, not HTTP response."""
    csv = "\n".join(list_data)
    conn.sendall(csv)

def main():
    """See notes at top of file."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 3575))
    listener.listen(1)

    while (True):
        (conn, _) = listener.accept()
        req = conn.recv(2048)
        query = json.load(req)
        list_csv = get_list_with_attrs(query["url"], query["attrs"])
        send_csv(conn, list_csv)
        
        print("\n\n\033[0;32mRetrival complete, and data sent!\033[0m\n")

if (__name__ == "__main__"):
    main()
