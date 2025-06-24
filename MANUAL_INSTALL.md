# Manual Installation Guide

For those who don't have / want to use a Python package management tool.

## Linux/MacOS

The best way to install a Python CLI app is via a virtual environment, and link it to the default path for your shell.

The module setup is also compatible with Poetry, so if you'd prefer to use that instead, you are welcome to.

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

## Windows

Since this is a Python app, you can follow essentially the same steps on Windows as on Linux/MacOS (especially if you're using Git Bash), with a couple tweaks. Here's the process on Windows: 

1. Open up the Command Prompt (`cmd.exe`), and then execute `pwsh` (start PowerShell session).

2. Clone the repo, and enter the folder 
    ```
    git clone https//github.com/lmr97/letterboxd_get_list
    cd letterboxd_get_list      # yep, cd works in PowerShell!
    ```

3. Create a Python virtual environment (this step is pretty much identical to the Linux/MacOS):

    ```
    py -m venv ./lb-venv   # forward slashes are valid in PowerShell!
    ```

4. Install the `letterboxd_list` module in this virtual environment:

    ```
    lb-venv/Scripts/pip install ./letterboxd_list
    ```

5. Find and copy the absolute path to the folder containing `lblist.exe` within the virtual environment (it's probably going to be something like `C:\path\to\repo\lb-venv\Scripts`).

6. Add this path to your shell's path. Here's [a great blog post](https://www.eukhost.com/kb/how-to-add-to-the-path-on-windows-10-and-windows-11/) on how to do so on Windows.


## Getting updates (manual install)

Since updates are pushed here though GitHub, getting updates is easy: Simply navigate back to where you cloned the repository, then run:

```
git pull
./lb-venv/bin/pip install --upgrade ./letterboxd_list
```