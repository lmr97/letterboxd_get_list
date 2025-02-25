# letterboxd_get_list

This repo has a CLI program that can convert any Letterboxd list into a CSV file, and get any desired information for each film in the list (title and year are added by default). It also has a `LetterboxdFilm` class definition (upon which `get_list.py` depends), which allows for quick access to film information off Letterboxd given the URL to the film.

## Installation

Clone the respoitory:

```
git clone https//github.com/lmr97/letterboxd_get_list
cd letterboxd_get_list
```

Then install dependencies with Poetry:

```
poetry install
```

Then run with Poetry. For example:

```
poetry run python get_list.py --list-url https://letterboxd.com/crew/list/2024-highest-rated-films/ --attributes director watches avg_rating --output-file 2024-highest-rated.csv
```

### Docker container

There is a GitHub Package for this repo called `letterboxd_get_list` which runs out of a Docker container (linked in the Packages section in the sidebar). You can pull the image with the command below, or build it yourself with the Dockerfile included here. 

```
docker pull ghcr.io/lmr97/letterboxd_get_list:latest
```

For easy retrieval of output files, I would recommend binding a folder to the container when you run it, like so:

```
mkdir OutputFiles                        # optional
docker run -d \
    --name get-lb-list \
    -v "${pwd}"/OutputFiles:/home/runner/OutputFiles
    letterboxd_get_list:latest
```

## `get_list.py` CLI usage

```
get_list.py [-h] -u, --list-url LIST_URL
                [-a, --attributes VALID_ATTRIBUTE [...]]
                [-o, --output-file OUTPUT_FILE]
```

Abbreviated options are accepted as well. In a bit more detail:

Option | Descriptions
------------ | ---------------
`--help`, `-h` | Print usage and help.
`--list-url`, `-u`| **(Required)** The URL for the list on Letterboxd you'd like to convert to a CSV file.
`--attributes`, `-a` | **(Optional)** A series 1 or more of kinds of information about each film you would like included in the output, from the list of valid attributes below. 
`--output-file`, `-o` | **(Optional)** A path/file to place the output. If none is given, this option will default to a filename will default to the last part of the URL, with `.csv` at the end, placed in the working directory (e.g. for `https://letterboxd.com/user/list/name-of-list/`, the file name would be `name-of-list.csv`).

The valid attribute arguments are as follows:

* actor
* additional-directing
* additional-photography
* art-direction
* assistant-director
* avg_rating
* camera-operator
* casting
* choreography
* cinematography
* composer
* costume-design
* country
* director
* editor
* executive-producer
* genre
* hairstyling
* language
* lighting
* likes
* makeup
* mini-theme
* original-writer
* producer
* production-design
* set-decoration
* songs
* sound
* special-effects
* special-effects
* story
* studio
* stunts
* theme
* title-design
* visual-effects
* watches
* writer

Additional notes about output formatting:

* For ranked lists, the rank is added as the first column. For non-ranked lists, this column is omitted.
* For films where a given attribute is not found on the page, the program writes "Not listed" in that cell (it does not crash).
* If an attribute has multiple values to it (e.g. the film has 3 directors), each element in that attribute will be separated by a `;`. In the case of casting, the key-value pairs (see `get_casting()` heading below) will be separated by a semicolon as well, with the key separated from the value by a colon as is convention.
* For films that have a comma in the title, the comma is removed so as to not mess up the CSV file. 

A loading bar will display to show the progress, and once the program has written to the output file, it will print `Retrieval complete!` and terminate. The first few lines of the CSV that results from the above command is shown below:

```
Rank,Title,Year,Director,Watches,Avg_rating
1,Harakiri,1962,Masaki Kobayashi,143603,4.69
2,Come and See,1985,Elem Klimov,320234,4.64
3,12 Angry Men,1957,Sidney Lumet,959305,4.62
4,Seven Samurai,1954,Akira Kurosawa,370612,4.6
5,The Godfather: Part II,1974,Francis Ford Coppola,1127168,4.59
...
```

## `LetterboxdFilm` class

This class takes care of all the requesting and parsing of HTML files for a give film's Letterboxd page, so the information is easily accessible to the user. Object initialization only requires the URL of the film. This After initialization, the following information is available as class attributes:

* Title
* Year
* Film page URL
* Film page HTML

These attributes are all `str`s. Any other information of the film comes through class methods that query the HTML via CSS selectors, a kind of lazy evaluation to save initalization time and storage space. I intended it to be quite intuitive, but I feel the methods below warant further description:

### `get_tabbed_attribute(attribute)`

**Returns**: `list`

This method returns data from the tabbed section of a Letterboxd film page where the cast, crew, details, genres, and releases info is (except for the Releases tab, as this section follows a different structure).

It will return `["Not listed"]` (a list with that string as its only element) if the attribute was not found for the given film, whether it was a valid attribute or not. An invalid argument warning is printed after a ValueError is raised if the attribute is not valid.

Always use the full, singular form of the attribute you'd like, and replace each space with a `-` (ASCII 45). 

See example below:

```
>>> film = LetterboxdFilm("https://letterboxd.com/film/rango")
>>> film.get_tabbed_attribute("assistant-director")
>>> ['Adam Somner', 'Ian Calip']
```

### `get_casting()`

**Returns**: `dict`

This method returns a dictionary that encodes the casting of a film, with the actor's names as keys, and the characters they play as values. 

## Feedback

Feel free to let me know if anything is going wrong as you use the program or class, don't hesitate to open a GitHub issue for it on this repository. If there is some functionality you'd like to see added, fork the repo, and submit a pull request here. 
