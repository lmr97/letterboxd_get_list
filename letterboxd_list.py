"""
Includes the classes used for get_list.py.
"""
import re
import copy
from pycurl import Curl
from selectolax.parser import HTMLParser

TABBED_ATTRS = ["actor",
                "additional-directing",
                "additional-photography",
                "art-direction",
                "assistant-director",
                "casting",
                "camera-operator",
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
                "writer"
                ]

class RequestError(Exception):
    """
    equivalent to 4xx errors
    """

class HTTPError(Exception):
    """
    To catch separate errors from 4xx ones
    """


class LetterboxdList:
    """
    Composition of `LetterboxdFilm`s, each of which are lazily initialized.
    Until they are, they exist as a `list` of URL strings. When needed,
    they are evaluated on-demand with the `.init_film(n)` function, which 
    initialized the nth film, and replaces its URL string in the list with
    a `LetterboxdFilm` object initialized with that URL.

    The inner `list` is accesible via indexing both with `int`s, and slices.
    Since it is intended to correspond to a static webpage, it is a read-only 
    attribute. The object can also be iterated over like a list. In short, 
    a `LetterboxdList` can be treated like a standard `list`! Just without 
    element re-assignment, of course.
    """
    def __init__(self, url: str, sub_init=False):
        """
        Initialize a `LetterboxdList` object.
        `sub_init` option allows you to initialize all URLs in the list 
        into LetterboxdFilm objects. This is not done by default as it 
        is time-intestive, since each initialization depends on at least
        1 HTTP request.
        """

        self._url  = url
        self._curl = Curl()
        self._curl.setopt(
            self._curl.HTTPHEADER,
            ["User-Agent: Application", "Connection: Keep-Alive"]
        )
        self._curl.setopt(self._curl.URL, url)
        first_page_html = HTMLParser(self._curl.perform_rs())
        self._length    = self._get_list_len(first_page_html)

        page_num_nodes  = first_page_html.css("li.paginate-page > a")
        self._num_pages = int(page_num_nodes[-1].text()) if len(page_num_nodes) > 0 else 1
        self._is_ranked = bool(first_page_html.css("p.list-number"))

        self._films     = self._get_urls(first_page_html)

        if sub_init:
            for n in range(self._length):
                self.init_film(n)


    def _get_list_len(self, html_dom: HTMLParser) -> int:
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
        number_re = re.compile("[0-9,]+")
        len_match = re.search(number_re, list_desc)         # gets first match
        list_len  = int(len_match[0].replace(",", ""))      # cast to int for transmission

        return list_len


    def _get_urls(self, first_page: HTMLParser):
        """
        Fetches all the URLs to films, across all list pages.
        """
        # we already have the first page, so start with the URLs there
        film_urls = [
            "https://letterboxd.com" + el.attrs['data-target-link'] \
            for el in first_page.css("div[data-target-link^='/film/']")
            ]

        if self._num_pages > 1:
            # now we do the rest, if there is any
            for current_page in range(2, self._num_pages+1): # exclude the first page, include last

                self._curl.setopt(self._curl.URL, self._url+"page/"+str(current_page)+"/")
                listpage = self._curl.perform_rs()
                tree = HTMLParser(listpage)

                film_urls.extend([
                    "https://letterboxd.com" + el.attrs['data-target-link'] \
                    for el in tree.css("div[data-target-link^='/film/']")
                    ])

        return film_urls


    def __getitem__(self, idx: int | slice):
        """
        This function implements the indexing syntax for the class, 
        including slicing. 
        
        If a slice is used, a deep copy of the original LetterboxdList 
        object is returned, with its contents being a subset of the original's.
        Otherwise, the list item is simply returned.

        Note that this list may contain both `str`s (URLs to films) and 
        `LetterboxdFilm` objects: it starts with only `str`s, but will contain
        only `LetterboxdFilm` objects if all have been initialized. 

        Any index or key errors will be handled by the containers indexed into.
        """

        # if the slice is equivalent to an int
        if isinstance(idx, int):
            return self._films[idx]

        # since Curl objects don't support deep copying, I need to delete that attribute
        # before the copy, and recreate it after (for both self and the copy)
        self._curl         = None
        subset_list        = copy.deepcopy(self)
        subset_list._films = subset_list._films[idx]

        self._curl = Curl()
        self._curl.setopt(
            self._curl.HTTPHEADER,
            ["User-Agent: Application", "Connection: Keep-Alive"]
        )
        subset_list._curl = self._curl

        return subset_list

    def __iter__(self) -> list:
        """
        Make the object iterable. Simply returns an iterater to the inner list.
        """
        return self._films.__iter__()

    @property
    def is_ranked(self) -> bool:
        """
        Whether the list is ranked or not.
        """
        return self._is_ranked

    @property
    def length(self) -> int:
        """
        Total films.
        """
        return self._length

    @property
    def film_list(self) -> list:
        """
        This returns the inner list, as is; it may be partially initialized.
        """
        return self._films

    @property
    def num_pages(self) -> int:
        """
        The number of pages the list takes up on Letterboxd.
        """
        return self._num_pages

    @property
    def url(self) -> str:
        """
        The list's URL.
        """
        return self._url


    def is_initialized(self, n: int) -> bool:
        """
        Checks to see if the nth element of the list is initialized
        as a LetterboxdFilm.
        """
        return isinstance(self._films[n], LetterboxdFilm)


    def init_film(self, n: int):
        """
        Initialize the nth film in the list of URLs (zero-indexed), 
        and swap the `str` at that position for the initialized 
        LetterboxdFilm object. 

        If the list item has already been initialized, the function
        simply returns the already-initialized object.
        """
        if isinstance(self._films[n], LetterboxdFilm):
            return self._films[n]

        lbf = LetterboxdFilm(self._films[n])
        self._films[n] = lbf

        return lbf



class LetterboxdFilm:
    """
    This class gets the HTML for the pages relevant to a film on Letterboxd,
    providing a simple interface for the film page's HTML.

    The following information is retreived and stored as attributes upon 
    initialization (all as `str` variables):
    - Title
    - Year
    - Film page URL
    - Film page HTML

    Any other film information is accessed through CSS-based searches on the HTML, implemented
    as class methods.

    It also takes an optional argument, `curl_session`, to use an existing PyCurl object.
    """
    def __init__(self, film_url: str, curl_session=None):

        self._url       = film_url
        insert_index    = film_url.find("/film")
        stats_url       = film_url[:insert_index] + "/csi" + film_url[insert_index:] + "stats/"
        self._stats_url = stats_url

        if curl_session is None:
            self.curl   = Curl()
            self.curl.setopt(self.curl.HTTPHEADER, ["User-Agent: Application"])
        else:
            self.curl   = curl_session

        self.curl.setopt(self.curl.URL, film_url)

        resp_str        = self.curl.perform_rs()
        status_code     = self.curl.getinfo(self.curl.RESPONSE_CODE)

        if status_code != 200:
            if 400 <= status_code < 500:
                raise RequestError(f"\nInvalid URL: {film_url}\nStatus code: {status_code}\n")
            if status_code >= 500:
                raise HTTPError(
                    "Letterboxd server issue. Try again later.\nStatus code: {status_code}\n"
                    )
            raise HTTPError(f"Unusual response from server; status code: {status_code}\n")

        page_html        = HTMLParser(resp_str)
        self._html       = page_html
        self._title      = page_html.css("span.js-widont")[0].text()
        year_el          = page_html.css("a[href^='/films/year/']")

        if len(year_el) == 0:
            self._year   = "((not found))"
        else:
            self._year   = year_el[0].text()

        # initialize on first time used
        self._stats_html = None



    @property
    def url(self) -> str:
        """
        URL at which the film can be found on Letterboxd.
        """
        return self._url

    @property
    def title(self) -> str:
        """
        Film title.
        """
        return self._title

    @property
    def year(self) -> str:
        """
        Release year. Note: this will return ((not found)) for some
        if not all unreleased films listed on the site.
        """
        return self._year

    @property
    def page_html(self) -> str:
        """
        The full HTML (as a `str`) of the webpage for the film.
        """
        return self._html.html


    def get_attrs_csv(self, attrs: list) -> str:
        """
        Gets a list of attributes and formats it as a CSV line (without initial or 
        terminal commas). 
        
        `dicts` and lists are formatted like so in the CSV string (not quote-enclosed):
        
        `dict`s:
        ```
        "key1: value1; key2: value2; ..."
        ```

        `list`s:
        ```
        "element1; element2; element3; ..."
        ```
        """
        attr_line = ""

        for attr in attrs:

            found_attr = "(not found)"              # default
            if attr in TABBED_ATTRS:
                found_attr = self.get_tabbed_attribute(attr)
            else:
                match attr:
                    case "avg-rating":  found_attr = self.get_avg_rating()
                    case "cast-list":   found_attr = self.get_casting()
                    case "likes":       found_attr = self.get_likes()
                    case "watches":     found_attr = self.get_watches()

            # convert list or dict to CSV-friendly format, if requested
            if   isinstance(found_attr, list):

                found_attr = "; ".join(found_attr)  # separate list elements by ";", not ","
                attr_line += "," + found_attr

            elif isinstance(found_attr, dict):

                found_attr = [f"{key}: {value}" for (key, value) in found_attr.items()]
                found_attr = "; ".join(found_attr)
                attr_line += "," + found_attr

            else:
                attr_line += "," + str(found_attr)

        return attr_line


    def get_tabbed_attribute(self, attribute: str) -> list:
        """
        Returns data from the tabbed section of a Letterboxd film page 
        where the cast, crew, details, genres, and releases info is  
        (except for the Releases tab, as this section follows a different 
        structure).

        Will return `["(not found)"]` (a list with that string as its 
        only element) if the attribute was not found for the given film, 
        whether it was a valid attribute or not. An invalid argument warning is 
        printed after a ValueError is raised if the attribute is not valid.
        
        Always use the full, singular form of the attribute you'd like, and replace each space
        with a hyphen, `-` (ASCII 45). 

        See example below:

        ```
        >>> film = LetterboxdFilm("https://letterboxd.com/film/rango")
        >>> film.get_tabbed_attribute("assistant-director")
        >>> ['Adam Somner', 'Ian Calip']
        ```
        """

        if attribute not in TABBED_ATTRS:

            print("\nINVALID ARGUMENT ", "\"", attribute, "\" passed to ",
                  "LetterboxdFilm.get_tabbed_attribute()\n",
                  "\nEXPLANATION: This film information is either not in the HTML by that name,\n",
                  "     or there is no method imlemented to retireve it yet. \n",
                  "SUGGESTED ACTION: If it seems like the latter is the case, \n",
                  "     please open up a GitHub issue and I will work on \n",
                  "     implementing a method to retrieve the information. \n",
                  "     You can also submit a pull request and implement it yourself.\n",
                  sep="")
            raise ValueError

        elements = self._html.css("a[href*='/" + attribute + "/']")

        # extract text from found HTML elements,
        # stripping out whitespace and commas
        attribute_list = [e.text().strip().replace(",","") for e in elements]

        # Remove plural and singluar versions of occurrences 
        # of the attribute name in the list, because sometimes that happens
        attr_versions = [
            attribute,
            attribute+"s",
            attribute.capitalize(),
            attribute.capitalize()+"s"
        ]
        for av in attr_versions:
            if av in attribute_list:
                attribute_list.remove(av)

        # return only distinct values, but still as a list
        if attribute_list: 
            return list(set(attribute_list))

        # the outcome whether the attribute was not valid or valid but not found for the film
        return ["(not found)"]


    def get_directors(self) -> list:
        """
        For some films, there are multiple directors (e.g. The Matrix (1999)), 
        so this method always returns a list.
        """
        return self.get_tabbed_attribute("director")
    
    def get_genres(self) -> list:
        return self.get_tabbed_attribute("genre")
    
    def get_countries(self) -> list:
        return self.get_tabbed_attribute("country")
    
    def get_studios(self) -> list:
        return self.get_tabbed_attribute("studio")
    
    def get_actors(self) -> list:
        return self.get_tabbed_attribute("actor")
    
    def get_themes(self) -> list:
        return self.get_tabbed_attribute("theme")

    def get_avg_rating(self) -> float:
        """
        Get average rating on Letterboxd.
        """
        rating_element = self._html.css("meta[name='twitter:data2']")

        avg_rating = None
        if len(rating_element) > 0:
            rating_element_content = rating_element[0].attributes['content']
            rating_element_title_parsed = rating_element_content.split(" ")
            avg_rating = float(rating_element_title_parsed[0])

        return avg_rating


    def get_casting(self) -> dict:
        """
        Returns a `dict` with the actor names as keys, 
        and character names as values.

        For casting director, use `get_tabbed_attribute("casting")`.
        """
        actor_nodes = self._html.css("a[href*='/actor/']")

        casting = {}
        for node in actor_nodes:

            # sometimes, people link actors in reviews; gotta filter those out
            try:
                node.attrs['title']
            except KeyError:
                continue

            casting[node.text()] = node.attrs['title']

        return casting


    # Statistics section

    def _get_stats_html(self):
        self.curl.setopt(self.curl.URL, self._stats_url)
        stats_response   = self.curl.perform_rs()
        stats_html       = HTMLParser(stats_response)
        self._stats_html = stats_html

    def get_watches(self) -> int:
        if (not self._stats_html):
            self._get_stats_html()

        watches_msg = self._stats_html.css("a.icon-watched")[0].attrs['title']
        watches_msg = watches_msg[11:]                       # take out the "Watched by"
        watches_msg = watches_msg[:-8]                       # take out the " members"
        view_count  = watches_msg.replace(",", "")           # take out commas

        return view_count
    
    def get_likes(self) -> int:
        if (not self._stats_html):
            self._get_stats_html()

        likes_msg = self._stats_html.css("a.icon-liked")[0].attrs['title']
        likes_msg = likes_msg[9:]                          # take out the "Liked by"
        likes_msg = likes_msg[:-8]                         # take out the " members"
        likes_count = likes_msg.replace(",", "")           # take out commas

        return likes_count

