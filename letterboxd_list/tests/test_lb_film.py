"""
Test the containers to make sure the information they get 
is accurate and consistent.
"""
from os.path import dirname, realpath
import csv
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
        lbc.LetterboxdFilm("https://httpbin.org/status/500")  # site designed to return 500 every time

    # test unusual code
    with pytest.raises(lbc.HTTPError):
        lbc.LetterboxdFilm("https://httpbin.org/status/303")

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
    # test value retrieved 20 October 2025, 8:58pm (MDT).
    fresh_film = lbc.LetterboxdFilm("https://letterboxd.com/film/dragons-heaven/")
    assert fresh_film.get_likes() - 1412 < 50

    true_likes = RAND_LIST_DF['Likes']
    test_likes = pd.Series([f.get_likes() for f in RANDOM_FILMS])

    # likes update past the static file's counts, so there needs to be
    # a margin of error
    assert (true_likes - test_likes < 20).all()


def test_avg_rating():
    true_avg_ratings = RAND_LIST_DF['Avg Rating']
    test_avg_ratings = pd.Series([f.get_avg_rating() for f in RANDOM_FILMS])

    try:
        # apparently these change enough to need a margin of error
        assert (true_avg_ratings - test_avg_ratings < 0.02).all()
    # If one of the films fails, the following will show which ones failed
    # (Technically it will only show the FIRST failure, but I hope to be 
    # maintaining this often enough for that to be the only one when
    # I'm looking at it.)
    except AssertionError:
        
        for (i, true_rating) in true_avg_ratings.items():
            
            assert (true_rating - test_avg_ratings[i]) < 0.02, \
                f"fail on row {i+2}, with film {RAND_LIST_DF.iloc[i, 0]}"


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
    assert int(TEST_FILM.get_attrs_csv(["watches"])) - 459_000 < 10_000
    assert int(TEST_FILM.get_attrs_csv(["likes"]))   - 182_000 <  1_000

    rand_list_no_stats = RAND_LIST_DF.drop(["Watches", "Likes", "Avg Rating"], axis=1)
    rlns_cols          = rand_list_no_stats.columns
    rand_list_raw      = rand_list_no_stats.to_csv(index=False, quoting=csv.QUOTE_NONNUMERIC).split("\n")
    
    no_stats_cols = VALID_ATTRS
    no_stats_cols.remove("watches")
    no_stats_cols.remove("likes")
    no_stats_cols.remove("avg-rating")
    no_stats_cols.sort()                # to reflect sortation in the test-file

    for i, film in enumerate(RANDOM_FILMS):
        # there are 51 rows in the file, and only 50 films, will not raise OOB error
        true_row = rand_list_raw[i+1]
        test_row = ",".join(
            [
                lbc.quote_enclose(film.title),
                film.year,
                film.get_attrs_csv(no_stats_cols)
            ]
        )

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
            for j, (true_val, test_val) in enumerate(zip(true_row.split(","), test_row.split(","))):
                true_no_quotes = true_val.replace("\"","")
                test_no_quotes = test_val.replace("\"","")

                # if this fails, then there IS a meaningful difference between cell values.
                assert set(true_no_quotes.split("; ")) == set(test_no_quotes.split("; ")), \
                    f"film \"{film.title}\" ({film.year}) failed assertion for '{rlns_cols[j]}' attribute."
