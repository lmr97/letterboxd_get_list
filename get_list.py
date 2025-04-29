# The server translates HTTP GET request query into JSON bytes,
# and sends them here. since this program is directly
# # accessible to the network, it only uses the data format
# I will give it from the server, and send back text as a
# CSV stream of text.
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
# This script sends the CSV line by line as a byte stream,
# first sending 2 bytes to denote the total list size, then 
# for every list row, sending 2 bytes to indicate the row size 
# (in bytes), and then sending the row data.
#
# See custom_backend::lb_app_io.rs for how this data is transmitted
# to the client.

import json
import socket
import re
from pycurl import Curl
from selectolax.parser import HTMLParser
from LetterboxdFilm import LetterboxdFilm, TABBED_ATTRS

# parameters for streaming data to server
ENDIANNESS = 'big'
SIZE_BYTES = 2

# Superset of TABBED_ATTRS list in letterboxdFilm.py
VALID_ATTRS = []
with open("./valid-lb-attrs.txt", "r") as attr_file:
    VALID_ATTRS = attr_file.readlines()

VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]

class RequestError(Exception):
    """
    to distinguish my syntax errors from genuine 
    request errors made by client
    """
    pass

# get number of films: 
def send_list_len(html_dom: HTMLParser, conn: socket.socket):
    """
    Sends precisely 2 bytes that give the number of films in the list.

    It works by using a description <meta> element in the HTML header 
    that follows the form "A list of <number> films compiled on
    Letterboxd, including <film>..." etc. (The user-made description of the 
    list comes after this standard-issue desc., after "About this list:").
    """
    
    print(" -- Sending total est. len --")

    # the first element is the one we want
    descr_el  = html_dom.css("meta[name='description']")[0]
    list_desc = descr_el.attributes['content']

    # get first number in the descr. str (which is list length),
    # using a regex search
    number_re = re.compile("[0-9]+")
    len_match = re.search(number_re, list_desc)         # gets first match
    list_len  = int(len_match[0])                       # cast to int for transmission

    # send it off!
    int_as_bytes = list_len.to_bytes(SIZE_BYTES, ENDIANNESS)
    conn.sendall(int_as_bytes)

def send_list_len_err(conn: socket.socket):
    """
    List length still needs to be sent regardless, but on an error
    condition, it can be a constant (0).
    """
    list_len_err = 0
    int_as_bytes = list_len_err.to_bytes(SIZE_BYTES, ENDIANNESS)
    conn.sendall(int_as_bytes)

def get_csv_row(film: LetterboxdFilm, attrs: list, list_is_ranked: bool, list_rank: int):
    """
    Assemble a CSV-formatted row of the data from the 
    requested attributes, and return it as a `str`.
    """
    title = "\"" + film.title + "\""            # rudimentary sanitizing
    file_row = title+","+film.year

    for attr in attrs:

        found_attr = "(not found)"              # default
        if (attr in TABBED_ATTRS):
            found_attr = film.get_tabbed_attribute(attr)
        else:
            match attr:
                case "avg-rating":  found_attr = film.get_avg_rating()
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
    
    return file_row


def send_line(conn: socket.socket, line: str):
    """
    First sends exactly 2 bytes, containing the number of chars to be written
    out to the stream (so the server knows how many to read), then 
    sends that data as bytes.
    
    This size-then-data protocol is implemented because Rust's 
    std::io::read_to_string(), my first choice, reads until EOF is received,
    and Python doesn't provide a good way to send an EOF signal without 
    closing a connection. So, Rust's std::io::read_exact() had to be used,
    for which a set size of buffer must be specified.

    This function is also used to send error messages, using the same protocol.
    """
    print(" -- Sending line --")
    byte_row = bytes(line, 'utf-8')

    # send row length
    # needs to be byte length of row, to account for multi-byte characters
    row_len  = len(byte_row)   
    byte_len = row_len.to_bytes(SIZE_BYTES, ENDIANNESS)
    print(row_len)
    print(byte_len)
    conn.sendall(byte_len)

    # send row itself
    print(byte_row)
    conn.sendall(byte_row)


def get_list_with_attrs(query: dict, conn: socket.socket) -> None:
    """Gets the requested attributed from the films on a Letterboxd list."""

    attrs = query['attrs']   # for ease of access

    # config PyCurl and set up base URL
    curl = Curl()
    curl.setopt(curl.HTTPHEADER, ["User-Agent: Application", "Connection: Keep-Alive"])
    lb_list_url = f"https://letterboxd.com/{query['author_user']}/list/{query['list_name']}/"

    # get list's HTML (page 1)
    curl.setopt(curl.URL, lb_list_url)
    listpage       = curl.perform_rs()                

    # check URL validity. Must send a "list length"
    # of 0 in order for the server to take the right amount of bytes
    # for the error message.
    if (curl.getinfo(curl.HTTP_CODE) != 200):
        err_msg = f"Error in fetching webpage. Response status: {curl.getinfo(curl.HTTP_CODE)}"
        send_list_len_err(conn)
        raise RequestError(err_msg)

    # validate attrs. must occur here for a similar reason.
    if not set(attrs).issubset(VALID_ATTRS):
        send_list_len_err(conn)
        raise RequestError("Invalid attributes submitted.")

    # get number of pages
    tree           = HTMLParser(listpage)
    page_num_nodes = tree.css("li.paginate-page")     # finds all page number nodes
    num_pages      = max(1, len(page_num_nodes))      # guarantee num_pages is at least 1

    send_list_len(tree, conn)                         # send number of films to stream handler on server

    # see if list is ranked
    list_is_ranked = bool(tree.css("p.list-number"))  # casts empty list of nodes to False
    list_rank      = 1                                # defining if needed

    # compose header
    header = "Title,Year"
    for attr in attrs:
        header += "," + attr.capitalize()

    if (list_is_ranked):
        header = "Rank," + header

    send_line(conn, header)                           # send out file header

    # Scrap list, by page.
    # Start at 1, including num_pages value in iteration
    for current_page in range(1, num_pages+1): 

        # only get new HTML if after first iteration 
        # (it's already been gotten) during initialization
        if (current_page > 1):
            curl.setopt(curl.URL, lb_list_url+"page/"+str(current_page)+"/")
            listpage = curl.perform_rs()
            tree = HTMLParser(listpage)

        # get URLs of all films on the page
        # a list comprehension, if you can believe it
        film_urls = [
            "https://letterboxd.com" + el.attrs['data-target-link']
            for el in tree.css("div[data-target-link^='/film/']")
        ]

        # get individual film info, and transmit the film's info line
        for url in film_urls:
            
            film    = LetterboxdFilm(url, curl)
            csv_row = get_csv_row(film, attrs, list_is_ranked, list_rank)

            send_line(conn, csv_row)

            print(f"Info for {film.title} ({film.year}) fetched.")

            if (list_is_ranked):
                list_rank += 1

        if (current_page == num_pages):
            break

        current_page += 1
    
    # signal completion to server
    send_line(conn, "done!")


def main():
    """See notes at top of file."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(('0.0.0.0', 3575))
    listener.listen(1)
    print(f"Listening on {listener.getsockname()}")

    while (True):
        (conn, _) = listener.accept()
        try:
            req = conn.recv(2048).decode("utf-8")
            query = json.loads(req)

            # for Docker healthchecks
            if query == {"msg": "are you healthy?"}:
                print("yep, still healthy!")
                continue

            get_list_with_attrs(query, conn)

        except RequestError as req_err:
            print(req_err)
            send_line(conn, f"-- 400 BAD REQUEST -- {repr(req_err)}")
        except Exception as e:
            print(e)
            send_line(conn, f"-- 500 INTERNAL SERVER ERROR -- {repr(e)}")
        finally:
            conn.close()    # sends EOF, so that Rust server can read data sent
            continue
        
        print("\n\033[0;32mRetrival complete, and data sent!\033[0m\n")

if (__name__ == "__main__"):
    main()
