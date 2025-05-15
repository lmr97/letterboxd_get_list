"""
Test the containers to make sure the information they get 
is accurate and consistent.
"""
import pytest
import src.letterboxd_list.containers as lbc

LONG_LIST    = lbc.LetterboxdList("https://letterboxd.com/tediously_brief/list/what-is-reality/")

# not ranked
RANDOM_FILMS = lbc.LetterboxdList(
    "https://letterboxd.com/dialectica972/list/truly-random-films/", 
    sub_init=True
    )


def test_length():
    assert LONG_LIST.length == 1516

def test_name():
    assert LONG_LIST.name == "what is reality?"

def test_list_url():
    assert LONG_LIST.url == "https://letterboxd.com/tediously_brief/list/what-is-reality/"

def test_is_init():
    assert RANDOM_FILMS.is_initialized(6)

def test_page_num():
    assert LONG_LIST.num_pages == 16

def test_indexing():
    true_titles = ["Christmas Waltz", "The Exterminating Angels", "The Novelist's Film"]

    # to make sure the case where stats_html has already been initialized
    # is covered in the test. See final line of test for follow-up.
    RANDOM_FILMS[11].get_watches()

    test_slice  = RANDOM_FILMS[10:13]
    assert isinstance(test_slice, lbc.LetterboxdList)

    for i, film in enumerate(test_slice):
        assert isinstance(film, lbc.LetterboxdFilm)
        assert true_titles[i] == film.title

    assert RANDOM_FILMS[19].title == "The Woman in the Fifth"

    # make sure the cool feature of Python indexing works
    assert RANDOM_FILMS[-1].title == "Story of Kale: When Someone's in Love"

    with pytest.raises(TypeError):
        RANDOM_FILMS['beetus']

    # this line ensures that the copied stats_html is still usable, since
    # `RANDOM_FILMS[11]` (see above) is the same film as `test_slice[1]`.
    # As long as this runs without error, it's okay. (the actual 
    # `get_likes()` function is tested elsewhere).
    test_slice[1].get_likes()

def test_rank():
    ranked_list = lbc.LetterboxdList(
    "https://letterboxd.com/dialectica972/list/worst-movies-i-have-ever-had-the-displeasure/"
        )
    assert ranked_list.is_ranked
    assert not RANDOM_FILMS.is_ranked
