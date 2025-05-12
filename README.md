# Letterboxd Lists to CSVs!

This repo has a CLI program that can convert any Letterboxd list into a CSV file, and get any desired information for each film in the list (title and year are added by default). It also has a `LetterboxdFilm` class definition (upon which `lblist` depends), which allows for quick access to film information off Letterboxd given the URL to the film.

**Please note: this program will take a while for long lists.** Since I have no API access for Letterboxd, the program has to make 1-2 HTTP GET requests for each film on the list. It ends up converting at a rate of about 2-4 films/second (faster for general info alone, slower if statistics are included). I've optimized as best I can given this, and I've provided a progress bar with the estimated time remaining on it so at least expectations can be set appropriately. 

## Installation 

### Using `pipx`

Installing with `pipx` is quite easy. Simply clone the repo and enter the directory:

```
git clone https//github.com/lmr97/letterboxd_get_list
cd letterboxd_get_list
```

Then install:

```
pipx install ./letterboxd_list
```

Now you have the executable `lblist` available!

### Without `pipx` (manually)

#### Linux/MacOS

The best way to install a Python CLI app is via a virtual environment, and link it to the default path for your shell.

1. Clone the respoitory:

    ```
    git clone https//github.com/lmr97/letterboxd_get_list
    cd letterboxd_get_list
    ```

2. Create a Python virtual environment (called `lb-venv`):

    ```
    python3 -m venv ./lb-venv
    ```

3. Install the module into this virtual environment:

    ```
    ./lb-venv/bin/pip install ./letterboxd_list
    ```

4. Create a [symbolic link](https://en.wikipedia.org/wiki/Symbolic_link) to a non-privileged part of your [`$PATH`](https://en.wikipedia.org/wiki/PATH_(variable)), for example:

    ```
    ln -s "$PWD/lb-venv/bin/lblist" ~/.local/bin/lblist
    ```

**Warning**: since the executable is symlinked, you can't move the folder where you defined the virtual environment (`lb-venv` in the commands above), or else you'll get "command not found"-type errors. This, of course, can be fixed by moving the virtual environment folder back into where you made it.

#### Windows

Since this is a Python app, you can follow essentially the same steps on Windows as on Linux/MacOS (especially if you're using Git Bash), with a couple tweaks. Here's the process on Windows: 

1. Open up the Command Prompt (`cmd.exe`), and then execute `pwsh` (start PowerShell session).

2. Clone the repo, and enter the folder 
    ```
    git clone https//github.com/lmr97/letterboxd_get_list
    cd letterboxd_get_list      # yep, cd works in PowerShell!
    ```

3. Create a Python virtual environment (this step is pretty much identical to the Linux/MacOS):

    ```
    python3 -m venv ./lb-venv   # forward slashes are valid in PowerShell!
    ```

4. Install the `letterboxd_list` module in this virtual environment:

    ```
    lb-venv/Scripts/pip install ./letterboxd_list
    ```

5. Find and copy the absolute path to the folder containing `lblist.exe` within the virtual environment (it's probably going to be something like `C:\path\to\repo\lb-venv\Scripts`).

6. Add this path to your shell's path. Here's [a great blog post](https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/) on how to do so on Windows.


## Getting updates

Since updates are pushed here though GitHub, getting updates is easy: Simply navigate back to where you cloned the repository, then run:

```
git pull
./lb-venv/bin/pip install --upgrade ./letterboxd_list
```

Note the `--upgrade` flag in the second command; that's where it differs from the initial install command.

Now you can run the executable as `lblist`! Here's an example:

```
lblist --list-url https://letterboxd.com/crew/list/2024-highest-rated-films/ \
    --attributes director watches avg-rating \
    --output-file 2024-highest-rated.csv
```


## `lblist` CLI usage

```
lblist [-h] -u, --list-url LIST_URL
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

* `actor`
* `additional-directing`
* `additional-photography`
* `art-direction`
* `assistant-director`
* `avg-rating`
* `camera-operator`
* `casting`
* `cast-list`
* `choreography`
* `cinematography`
* `composer`
* `costume-design`
* `country`
* `director`
* `editor`
* `executive-producer`
* `genre`
* `hairstyling`
* `language`
* `lighting`
* `likes`
* `makeup`
* `mini-theme`
* `original-writer`
* `producer`
* `production-design`
* `set-decoration`
* `songs`
* `sound`
* `special-effects`
* `studio`
* `stunts`
* `theme`
* `title-design`
* `visual-effects`
* `watches`
* `writer`

You can find this list in `valid-lb-attrs.txt`.

Additional notes about output formatting:

* For ranked lists, the rank is added as the first column. For non-ranked lists, this column is omitted.
* For films where a given attribute is not found on the page, the program writes "Not listed" in that cell (it does not crash).
* If an attribute has multiple values to it (e.g. the film has 3 directors), each element in that attribute will be separated by a `;`. In the case of casting, the key-value pairs (see `get_casting()` heading below) will be separated by a semicolon as well, with the key separated from the value by a colon as is convention.
* For films that have a comma in the title, the comma is removed so as to not mess up the CSV file. 

A loading bar will display to show the progress, and once the program has written to the output file, it will print `Retrieval complete!` and terminate. The first few lines of the CSV that results from the above command is shown below:

```
Rank,Title,Year,Director,Watches,Avg-rating
1,"Dune: Part Two",2024,Denis Villeneuve,2744519,4.4
2,"I'm Still Here",2024,Walter Salles,592017,4.33
3,"How to Make Millions Before Grandma Dies",2024,Pat Boonnitipat,113632,4.33
4,"Look Back",2024,Kiyotaka Oshiyama,278852,4.27
5,"Sing Sing",2023,Greg Kwedar,225983,4.28
...
```

## `LetterboxdFilm` class

This class takes care of all the requesting and parsing of HTML files for a give film's Letterboxd page, so the information is easily accessible to the user. Object initialization only requires the URL of the film. This After initialization, the following information is available as class attributes:

* Title
* Year
* Film page URL
* Film page HTML

These attributes are all `str`s. Any other information of the film comes through class methods that query the HTML via CSS selectors, a kind of lazy evaluation to save initalization time and storage space. I intended it to be as intuitive as possible, but I feel the methods below warant further description:

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

## `LetterboxdList` class

This class is a composition of the `LetterboxdFilm` class, and is designed to behave like a Python list, complete with slicing and iterators. It includes some basic data like the list's name, its length, and a list of film URLs to each film in the list. This list is kept as strings, because initializing them all as `LetterboxdFilm` objects is quite resource intensive. It can be done, however, by specifying `sub_init=True` in the constructor, and individually by calling `init_film(n)`, where `n` is the *n*th film in the list.

### Slicing

`LetterboxdList` instances support slicing! Note that the object returned via slicing is also a `LetterboxdList` with the same info (it's a deep copy). If you are simply indexing into the list, however, the object returned is either a string or a `LetterboxdFilm`, depending on if that list element has been initialized or not.

## Feedback

Feel free to let me know if anything is going wrong as you use the program or class, don't hesitate to open a GitHub issue for it on this repository. If there is some functionality you'd like to see added, fork the repo, and submit a pull request here. 
