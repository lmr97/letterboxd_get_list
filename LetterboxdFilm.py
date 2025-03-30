from pycurl import Curl
from selectolax.parser import HTMLParser

# Attributes that appear (consistently) in the central 
# tabbed section of a Letterboxd film page
TABBED_ATTRS = ["actor",
                "additional-directing",
                "additional-photography",
                "art-direction",
                "assistant-director",
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

        if (not curl_session):
            self.curl   = Curl()
            self.curl.setopt(self.curl.HTTPHEADER, ["User-Agent: Application"])
        else:
            self.curl   = curl_session
        
        self.curl.setopt(self.curl.URL, film_url)

        resp_str        = self.curl.perform_rs()
        status_code     = self.curl.getinfo(self.curl.RESPONSE_CODE)

        assert(status_code == 200)  # handled by main
        
        page_html        = HTMLParser(resp_str)
        self._html       = page_html
        self._title      = page_html.css("span.js-widont")[0].text()
        self._year       = page_html.css("a[href^='/films/year/']")[0].text()

        # initialize on first time used
        self._stats_html = None 
        


    @property
    def url(self):
        return self._url
    
    @property
    def title(self):
        return self._title
    
    @property
    def year(self):
        return self._year
    
    @property
    def page_html(self):
        return self._html.html


    def get_tabbed_attribute(self, attribute: str) -> list:
        """
        Returns data from the tabbed section of a Letterboxd film page 
        where the cast, crew, details, genres, and releases info is  
        (except for the Releases tab, as this section follows a different 
        structure).

        Will return `["(not listed)"]` (a list with that string as its 
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
            
        elements = self._html.css("a[href*='" + attribute + "']")

        # extract text from found HTML elements
        attribute_list = [e.text().strip() for e in elements]

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
        if (attribute_list):
            return list(set(attribute_list))

        # the outcome whether the attribute was not valid or valid but not found for the film
        else: return ["(not listed)"]
    
    
    def get_directors(self) -> list:
        """
        For some films, there are multiple directors (e.g. The Matrix (1999)), 
        so this method always returns a list.
        """
    
        return self.get_tabbed_attribute("director")
    
    def get_genres(self) -> list:
        return self.get_tabbed_attribute("genre")
    
    def get_countries(self) -> list:
        return countries
    
    def get_studios(self) -> list:
        return self.get_tabbed_attribute("studio")
    
    def get_actors(self) -> list:
        return self.get_tabbed_attribute("actor")
    
    def get_themes(self) -> list:
        return self.get_tabbed_attribute("theme")

    def get_avg_rating(self) -> float:
        rating_element = self._html.css("meta[name='twitter:data2']")
    
        avg_rating = None
        if (len(rating_element) > 0):
            rating_element_content = rating_element[0].attributes['content']
            rating_element_title_parsed = rating_element_content.split(" ")
            avg_rating = float(rating_element_title_parsed[0])

        return avg_rating


    def get_casting(self) -> dict:
        """
        Returns a `dict` with the actor names as keys, 
        and character names as values.
        """
        actor_nodes = self._html.css("a[href*='/actor/']")

        casting = {}
        for node in actor_nodes:

            # sometimes, people link actors in reviews; gotta filter those out
            try: node.attrs['title']
            except (KeyError): continue

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



        
