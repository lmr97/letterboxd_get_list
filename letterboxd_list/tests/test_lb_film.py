"""
Test the containers to make sure the information they get 
is accurate and consistent.
"""
from os.path import dirname, realpath
import json
import pytest
import src.letterboxd_list.containers as lbc
from src.letterboxd_list import VALID_ATTRS
import pandas as pd     # needed for a good csv reader

RANDOM_FILMS  = lbc.LetterboxdList(
    "https://letterboxd.com/dialectica972/list/truly-random-films/", 
    sub_init=True
    )
PATH_TO_TESTS = dirname(realpath(__file__))
RAND_LIST_DF  = pd.read_csv(PATH_TO_TESTS+"/random-list-test.csv")
TEST_FILM     = lbc.LetterboxdFilm("https://letterboxd.com/film/stalker/")
TEST_FILM_URL = "https://letterboxd.com/film/stalker/"


# The simple stuff

def test_year():
    true_years = RAND_LIST_DF['Year'].apply(str)
    test_years = pd.Series([f.year for f in RANDOM_FILMS])

    assert (true_years == test_years).all()

    # an "upcoming" film that will probably never get released
    empty_year = lbc.LetterboxdFilm("https://letterboxd.com/film/sherlock-holmes-3/")
    assert empty_year.year == "(not listed)"

def test_title():
    true_titles = RAND_LIST_DF['Title']
    test_titles = pd.Series([f.title for f in RANDOM_FILMS])

    assert (true_titles == test_titles).all()

def test_get_url():
    assert TEST_FILM.url == TEST_FILM_URL

def test_http_errors():
    with pytest.raises(lbc.RequestError):
        lbc.LetterboxdFilm("https://letterboxd.com/films/a-film-that-isnt-on-lb/")

    with pytest.raises(lbc.HTTPError):
        lbc.LetterboxdFilm("https://httpstat.us/500")  # site designed to return 500 every time

    # test unusual code
    with pytest.raises(lbc.HTTPError):
        lbc.LetterboxdFilm("https://httpstat.us/303")

def test_bad_tabbed_attr():
    with pytest.raises(ValueError):
        TEST_FILM.get_tabbed_attribute("bingus")

def test_equality_operator():
    """
    `init_film()` is used here for the purpose of coverage.
    """
    assert RANDOM_FILMS[18] == RANDOM_FILMS.init_film(18)
    assert not RANDOM_FILMS[18] == RANDOM_FILMS.init_film(19)
    with pytest.raises(ValueError):
        RANDOM_FILMS[18] == "not a LetterboxdFilm object"


# The interesting stuff

def test_watches_method():
    true_watches = RAND_LIST_DF['Watches']
    test_watches = pd.Series([f.get_watches() for f in RANDOM_FILMS])

    # watches update past the static file's counts, so there needs to be
    # a margin of error
    assert (true_watches - test_watches < 30).all()


def test_likes_method():

    # to cover the case where the stats_html private attribute hasn't been initialized.
    # test value retrieved 14 May 2025, 9:08pm (MDT).
    fresh_film = lbc.LetterboxdFilm("https://letterboxd.com/film/dragons-heaven/")
    assert fresh_film.get_likes() - 1200 < 50

    true_likes = RAND_LIST_DF['Likes']
    test_likes = pd.Series([f.get_likes() for f in RANDOM_FILMS])

    # likes update past the static file's counts, so there needs to be
    # a margin of error
    assert (true_likes - test_likes < 20).all()


def test_avg_rating():
    true_avg_ratings = RAND_LIST_DF['Avg Rating']
    test_avg_ratings = pd.Series([f.get_avg_rating() for f in RANDOM_FILMS])

    # apparently these change enough to need a margin of error
    assert (true_avg_ratings - test_avg_ratings < 0.02).all()


def test_get_cast_list():
    """
    This test compares the data, not the formatting of the cast lists.
    CSV formatting is checked in `test_csv_attrs()`.
    """
    true_cast_lists_strs = RAND_LIST_DF['Cast List']

    for true_cast_str, film in zip(true_cast_lists_strs, RANDOM_FILMS):
        test_cast_dict = film.get_cast_list()

        # format for JSON deserialization
        true_cast_dict = {}
        if true_cast_str != "(not listed)":
            true_cast_str  = true_cast_str.replace("; ", "\", \"").replace(": ", "\": \"")
            true_cast_str  = "{\""+true_cast_str+"\"}"
            true_cast_dict = json.loads(true_cast_str)

        assert true_cast_dict == test_cast_dict, \
            f"film \"{film.title}\" ({film.year}) failed assertion."


def test_csv_attrs():
    """
    This test evaluates the formatting output by `get_attrs_csv()`.
    """
    # test trivial case
    assert TEST_FILM.get_attrs_csv([]) == ""

    # test conversion of string into list
    assert TEST_FILM.get_attrs_csv("country") == "\"USSR\""

    # test bad attribute
    with pytest.raises(ValueError):
        TEST_FILM.get_attrs_csv("bingus")

    # cover the stat branches in the function, with margins of error
    # test values retrieved 14 May 2025, 9:02pm (MDT).
    assert int(TEST_FILM.get_attrs_csv(["watches"])) - 407504 < 1000
    assert int(TEST_FILM.get_attrs_csv(["likes"]))   - 159679 < 1000

    # since we're checking CSV formatting, we need the raw text data,
    # but from a version without the stats (rating, likes, and watches)
    # since these change regularly, and are checked separately above.
    rand_list_raw = []
    with open(PATH_TO_TESTS+"/random-list-no-stats.csv", "r", encoding="utf-8") as rdr:
        rand_list_raw = rdr.readlines()

    no_stats_attrs = VALID_ATTRS
    no_stats_attrs.remove("watches")
    no_stats_attrs.remove("likes")
    no_stats_attrs.remove("avg-rating")
    for i, film in enumerate(RANDOM_FILMS):
        # there are 51 rows in the file, and only 50 films, will not raise OOB error
        true_row = rand_list_raw[i+1]
        test_row = ",".join(
            [
                lbc.quote_enclose(film.title),
                film.year,
                film.get_attrs_csv(no_stats_attrs)
            ]
        ) + "\n"

        # Sometimes the rows are not exactly identical only because the order of some names
        # in attributes may change on Letterboxd.com itself. This means that the test values
        # are fetched from different database than the touchstone data. This block is a
        # "closer look" to verify whether the content differs, or simply the order.
        try:
            assert true_row == test_row, f"film \"{film.title}\" ({film.year}) failed assertion."
        except AssertionError:
            # divide rows into cells, and check each cell for a difference in content.
            true_row = true_row.replace("\n", "")
            test_row = test_row.replace("\n", "")
            for true_val, test_val in zip(true_row.split(","), test_row.split(",")):
                true_no_quotes = true_val.replace("\"","")
                test_no_quotes = test_val.replace("\"","")

                # if this fails, then there IS a meaningful difference between cell values.
                assert set(true_no_quotes.split("; ")) == set(test_no_quotes.split("; ")), \
                    f"film \"{film.title}\" ({film.year}) failed assertion."
