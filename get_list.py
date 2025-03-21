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
#                   CSV text <- (this)
#                      |          ^
#            HTTP      v          |
#   Client  <---->   Server  ->  JSON
# 
# simple as.

import json
import socket
from pycurl import Curl
from selectolax.parser import HTMLParser
from LetterboxdFilm import LetterboxdFilm, TABBED_ATTRS
    
# TODO: correct cast/casting/casting-director
# [x] here
# [] README

# Superset of TABBED_ATTRS list in letterboxdFilm.py
VALID_ATTRS = []
with open("./valid-lb-attrs.txt", "r") as attr_file:
    VALID_ATTRS = attr_file.readlines()

VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]

def get_film_num_est():
    return


def get_list_with_attrs(query: dict) -> list:
    """Gets the requested attributed from the films on a Letterboxd list."""
    list_file = []
    unretrieved_attrs = []
    attrs = query['attrs']   # for ease of access

    curl = Curl()
    curl.setopt(curl.HTTPHEADER, ["User-Agent: Application", "Connection: Keep-Alive"])
    lb_list_url = f"https://letterboxd.com/{query['author_user']}/list/{query['list_name']}/"
    
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
            film = LetterboxdFilm(url, curl)            # handled by main

            title = "\"" + film.title + "\""            # rudimentary sanitizing
            file_row = title+","+film.year

            for attr in attrs:

                found_attr = "(not found)"              # default
                if (attr in TABBED_ATTRS):
                    found_attr = film.get_tabbed_attribute(attr)
                else:
                    match attr:
                        case "avg_rating":  found_attr = film.get_avg_rating()
                        case "cast-list":
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

            print(f"Info for {film.title} ({film.year}) fetched.")
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

    list_file.insert(0, header)
    return list_file


def send_csv(conn: socket.socket, list_data: list):
    """
    This function sends only the CSV content, not HTTP response.
    That is handled by the server.
    """
    csv       = "\n".join(list_data) + ""
    csv_bytes = bytes(csv, "utf-8")
    conn.sendall(csv_bytes)

def main():
    """See notes at top of file."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('127.0.0.1', 3575))
    listener.listen(1)
    bad_req = bytes("400 BAD REQUEST", "utf-8")
    print(f"Listening on {listener.getsockname()}")

    while (True):
        try:
            (conn, _) = listener.accept()
            req = conn.recv(2048).decode("utf-8")
            query = json.loads(req)
            print(query)

            list_csv = get_list_with_attrs(query)
            send_csv(conn, list_csv)
        except Exception as e:
            print(e)
            # send only the string "400 BAD REQUEST" and move on
            # to the next connection.
            # This is if somehow the client-side JavaScript 
            # (../static/scripts/lb-app.js) doesn't catch the invalid URL
            conn.sendall(bad_req) 
            continue
        finally:
            conn.close()    # sends EOF, so that Rust server can read data sent
        
        print("\n\033[0;32mRetrival complete, and data sent!\033[0m\n")

if (__name__ == "__main__"):
    main()
