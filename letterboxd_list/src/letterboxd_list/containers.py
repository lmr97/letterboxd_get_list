"""
Includes the central logic of the app encapsulated in the 
`LetterboxdList` and `LetterboxdFilm` classes.
"""
import re
import copy
import pycurl
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


def handle_http_err(status_code: int, url: str) -> None:
    """
    A common way to address HTTP errors when fetching letterboxd info.
    """
    if status_code != 200:
        if 400 <= status_code < 500:
            raise RequestError(f"\nInvalid URL: {url}\nStatus code: {status_code}\n")
        if status_code >= 500:
            raise HTTPError(
                "Letterboxd server issue. Try again later.\nStatus code: {status_code}\n"
                )
        raise HTTPError(f"Unusual response from server; status code: {status_code}\n")


def quote_enclose(string: str) -> str:
    """
    Defining this here to make the code more legible.
    """
    return "\""+string+"\""



class RequestError(ValueError):
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

    Note: ranking information is not kept, since it will always map one-to-one
    to the index of the film in the list, and the list is not designed to be
    modified. The `is_ranked` boolean allows the user to check and implement
    display of list rank as they see fit. 
    """
    def __init__(self, url: str, sub_init=False):
        """
        Initialize a `LetterboxdList` object.
        `sub_init` option allows you to initialize all URLs in the list 
        into LetterboxdFilm objects. This is not done by default as it 
        is time-intestive, since each initialization depends on at least
        1 HTTP request.
        """
        self._url       = url
        self._curl      = pycurl.Curl()
        self._curl.setopt(pycurl.URL, self._url)
        self._curl.setopt(
            pycurl.HTTPHEADER,
            ["User-Agent: Application", "Connection: Keep-Alive"]
        )

        first_page_html = HTMLParser(self._curl.perform_rs())
        resp_code       = self._curl.getinfo(pycurl.HTTP_CODE)
        handle_http_err(resp_code, self._url)

        self._name      = first_page_html.css(".title-1")[0].text()
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

                self._curl.setopt(pycurl.URL, self._url+"page/"+str(current_page)+"/")
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

        if isinstance(idx, slice):
            # since Curl objects don't support deep copying, I need to delete that attribute
            # before the copy, and recreate it after (for both self and the copy)
            self._curl         = None
            subset_list        = copy.deepcopy(self)
            subset_list._films = subset_list._films[idx]

            self._curl = pycurl.Curl()
            self._curl.setopt(
                pycurl.HTTPHEADER,
                ["User-Agent: Application", "Connection: Keep-Alive"]
            )
            subset_list._curl = self._curl

            return subset_list

        raise TypeError("LetterboxdList objects can only be indexed with `int`s or `slice`s.")


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
    def name(self) -> str:
        """
        The name of the list.
        """
        return self._name

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

    Any other film information is accessed through CSS-based searches on the 
    HTML, implemented as methods.
    """
    def __init__(self, film_url: str):

        self._url       = film_url
        insert_index    = film_url.find("/film")
        stats_url       = film_url[:insert_index] + "/csi" + film_url[insert_index:] + "stats/"
        self._stats_url = stats_url

        self._curl      = pycurl.Curl()
        self._curl.setopt(pycurl.HTTPHEADER, ["User-Agent: Application"])

        self._curl.setopt(pycurl.URL, film_url)

        resp_str        = self._curl.perform_rs()
        status_code     = self._curl.getinfo(self._curl.RESPONSE_CODE)
        handle_http_err(status_code, self._url)

        page_html       = HTMLParser(resp_str)
        self._html      = page_html
        self._title     = page_html.css("span.js-widont")[0].text()
        year_el         = page_html.css("a[href^='/films/year/']")

        if len(year_el) == 0:
            self._year  = "(not listed)"
        else:
            self._year  = year_el[0].text()

        # initialize on first time used
        self._stats_html = None

    def __eq__(self, other) -> bool:
        """
        Since URLs are unique to each film, and all that meaningfully 
        differentiates `LetterboxdFilm` objects is the film about which 
        they hold info, I define two instances as identical if they 
        share the same URL.
        """
        if isinstance(other, LetterboxdFilm):
            return self._url == other._url

        raise ValueError("Only LetterboxdFilm objects can be compared with each other using `==`.")


    def __deepcopy__(self, memo):
        """
        Since Curl objects cannot be deep-copied (and their specific config data isn't
        that important in this class), this class' deep copy has to be implemented 
        such that everything *but* the Curl object member is copied. 
        
        It essentially get reinitialized for both the source and the copy, since 
        it needs to be deleted for the duration of the copy process.

        Discovered thanks to this StackOverflow answer: https://stackoverflow.com/a/56478412
        """
        obj_copy = type(self).__new__(self.__class__)  # skips calling __init__

        # gotta do all this manually, to avoid infinite recursion
        obj_copy._url       = copy.deepcopy(self._url,        memo)
        obj_copy._stats_url = copy.deepcopy(self._stats_url,  memo)
        obj_copy._title     = copy.deepcopy(self._title,      memo)
        obj_copy._year      = copy.deepcopy(self._year,       memo)
        obj_copy._html      = HTMLParser(self._html.html)
        obj_copy._curl      = self._curl

        if self._stats_html:
            obj_copy._stats_html = HTMLParser(self._stats_html.html)
        else:
            obj_copy._stats_html = None

        return obj_copy


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
        Release year. Note: this will return ((not listed)) for some
        if not all unreleased films listed on the site.
        """
        return self._year


    def get_attrs_csv(self, attrs: list | str) -> str:
        """
        Gets a list of attributes and formats it as a CSV line (without initial or 
        terminal commas). 
        
        `dicts` and lists are formatted like so in the CSV string (quote-enclosed, as shown):
        
        `dict`s:
        ```
        "key1: value1; key2: value2; ..."
        ```

        `list`s:
        ```
        "element1; element2; element3; ..."
        ```
        """
        # trivial case
        if len(attrs) == 0:
            return ""

        # strings technically are accepted, but each character is treated as
        # an independent attribute. So enforce convert the string to a list.
        if isinstance(attrs, str):
            attrs = [attrs]

        attr_line = []
        for attr in attrs:

            found_attr = "(not listed)"              # default
            if attr in TABBED_ATTRS:
                found_attr = self.get_tabbed_attribute(attr)
            else:
                match attr:
                    case "avg-rating": found_attr = self.get_avg_rating()
                    case "cast-list":  found_attr = self.get_cast_list()
                    case "likes":      found_attr = self.get_likes()
                    case "watches":    found_attr = self.get_watches()

            if   isinstance(found_attr, list):
                # separate list elements by ";" not ","
                found_attr = quote_enclose("; ".join(found_attr))

            elif isinstance(found_attr, dict):

                if len(found_attr) == 0:
                    found_attr = "(not listed)"      # empty dicts need to be handled explicitly
                else:
                    found_attr = [f"{key}: {value}" for (key, value) in found_attr.items()]
                    found_attr = quote_enclose("; ".join(found_attr))

            # regardless
            attr_line.append(str(found_attr))

        return ",".join(attr_line)


    def get_tabbed_attribute(self, attribute: str) -> list:
        """
        Returns data from the tabbed section of a Letterboxd film page 
        where the cast, crew, details, genres, and releases info is  
        (except for the Releases tab, as this section follows a different 
        structure).

        Will return `["(not listed)"]` (a list with that string as its 
        only element) if the attribute was not found for the given film, 
        if it was a valid attribute. An invalid attribute passed to this
        function causes a `ValueError` to be raised.
        
        Always use the full, singular form of the attribute you'd like, and replace each space
        with a hyphen, `-` (ASCII 45). 

        Attributes with multiple values are ordered the same way they appear on Letterboxd. 
        The list of actors, for instance, preserves the billing order for the film. For 
        languages, the primary language is listed first, and any other spoken or secondary 
        languages are listed after.

        A usage example:

        .. code-block:: python
        
            >>> film = LetterboxdFilm("https://letterboxd.com/film/rango")
            >>> film.get_tabbed_attribute("assistant-director")
            ['Adam Somner', 'Ian Calip']

        """

        if attribute not in TABBED_ATTRS:

            # I'm building the error message like this to preserve the formatting.
            err_msg = [
                "\nINVALID ARGUMENT ", "\"", attribute, "\" passed to ",
                "LetterboxdFilm.get_tabbed_attribute()\n",
                "\nEXPLANATION: This film information is either not in the HTML by that name,\n",
                "     or there is no method imlemented to retireve it yet. \n",
                "SUGGESTED ACTION: If it seems like the latter is the case, \n",
                "     please open up a GitHub issue and I will work on \n",
                "     implementing a method to retrieve the information. \n",
                "     You can also submit a pull request and implement it yourself.\n"
                ]
            err_msg = "".join(err_msg)

            raise ValueError(err_msg)

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

        # director appears twice on every page, so only return unique values,
        # with order preserved (found here: https://stackoverflow.com/a/17016257)
        if attribute == "director" and len(attribute_list) > 0:
            return list(dict.fromkeys(attribute_list))

        if len(attribute_list) > 0:
            return attribute_list

        # the outcome whether the attribute was not valid or valid but not found for the film
        return ["(not listed)"]


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

        return float(avg_rating)


    def get_cast_list(self) -> dict:
        """
        Returns a `dict` with the actor names as keys, and character names as values.

        For casting director, use `get_tabbed_attribute("casting")`.
        """
        actor_nodes = self._html.css("a[href*='/actor/']")

        casting = {}
        for node in actor_nodes:

            # Some films, like in documentaries, the "actors" are all appearing
            # as themselves, not as a character. This catches those cases.
            if 'title' not in node.attributes.keys():
                casting[node.text()] = "Self"
                continue

            # double-quotes are reserved for the CSV formatting
            casting[node.text().replace("\"", "'")] = node.attributes['title'].replace("\"", "'")

        return casting


    # Statistics section

    def _get_stats_html(self):
        self._curl.setopt(pycurl.URL, self._stats_url)
        stats_response   = self._curl.perform_rs()
        stats_html       = HTMLParser(stats_response)
        self._stats_html = stats_html


    def get_watches(self) -> int:
        """
        Return the amount of watches the film has on Lettereboxd.
        """
        if not self._stats_html:
            self._get_stats_html()

        watches_msg = self._stats_html.css("a.icon-watched")[0].attrs['title']
        watches_msg = watches_msg[11:]                       # take out the "Watched by"
        watches_msg = watches_msg[:-8]                       # take out the " members"
        view_count  = watches_msg.replace(",", "")           # take out commas

        return int(view_count)

    def get_likes(self) -> int:
        """
        Return the amount of likes the film has on Letterboxd.
        """
        if not self._stats_html:
            self._get_stats_html()

        likes_msg = self._stats_html.css("a.icon-liked")[0].attrs['title']
        likes_msg = likes_msg[9:]                          # take out the "Liked by"
        likes_msg = likes_msg[:-8]                         # take out the " members"
        likes_count = likes_msg.replace(",", "")           # take out commas

        return int(likes_count)
