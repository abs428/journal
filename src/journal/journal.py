"""Journaling from the command line"""

import os
import json
import warnings
import click
from pathlib import Path
import typing as t
import sys
from subprocess import call

SETTINGS_FILE = "settings.json"  #: The file containing the configuration information

## Helper functions


def does_file_exist(filepath: str) -> bool:
    """Helper function that checks whether the file exists"""
    my_file = Path(filepath)
    return my_file.is_file()


def get_datadir() -> Path:
    """Returns a parent directory path
    where persistent application data can be stored.

    # linux: ~/.local/share
    # macOS: ~/Library/Application Support
    # windows: C:/Users/<USER>/AppData/Roaming

    Borrowed from https://stackoverflow.com/a/61901696/970897
    """

    home = Path.home()

    if sys.platform == "win32":
        return home / "AppData/Roaming"
    elif sys.platform == "linux":
        return home / ".local/share"
    elif sys.platform == "darwin":
        return home / "Library/Application Support"
    else:
        raise NotImplementedError("Supported platforms are: Windows, OSX, Linux.")


def get_settings_path() -> Path:
    """Returns the full path of the settings file"""
    return get_datadir() / f"journal/{SETTINGS_FILE}"


def get_settings() -> t.Dict[str, str]:
    """Function that returns the settings as a dict"""
    config = get_settings_path()
    if not does_file_exist(config):
        raise FileNotFoundError(f"Settings file not found at {config}")
    with open(config, "r") as f:
        settings = json.load(f)
    return settings


def create_settings(data: t.Dict[str, str]) -> None:
    """Creates a SETTINGS_FILE file that stores configuration info"""
    file_path = get_settings_path()

    if does_file_exist(file_path):
        raise ValueError(f"The settings file already exists at {file_path}")

    # BUG: This section for creating a folder if it doesn't exist
    # doesn't seem to be working on OSX/Linux.
    folder_path = os.path.basename(file_path)
    folder = Path(folder_path)
    folder.mkdir(exist_ok=True)  # Creating the folder

    with open(file_path, "w") as f:
        json.dump(data, f)


def get_post_name(
    name: str = None,
    date: str = None,
    day_format: str = "MMMM-D",
    date_format: str = "YYYY-MM-DD",
    sep: str = "-",
    ext: str = ".md",
) -> str:
    """Function that generates the filename for a journal post
    written in markdown. It creates a default post name if
    nothing is specified. The post entry refers to today's entry.

    Typically of the format: 2021-01-07-post-name

    TODO: Custom names from CLI
    """
    import arrow

    now = arrow.now()

    if date is None:
        date = now.format(date_format)
    else:
        raise NotImplementedError("Posts for custom dates not supported yet.")
    if name is None:
        name = now.format(day_format).lower()

    # FIXME: Hardcoding extension may not be a great idea
    return date + sep + name + ext


def display_dict(dictionary: t.Dict[str, str]) -> None:
    """Displays a nicely formatted dictionary with
    key value pairs on the terminal"""
    for key, value in dictionary.items():
        text = (click.style(key, fg="white", bold=True) + ": ").rjust(15) + value
        click.echo(text)


## CLI


@click.option("--config", is_flag=True, help="Displays the current settings.")
@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx, config):
    """Manage your journal entries from the terminal"""

    if config:
        settings = get_settings()
        display_dict(settings)
        click.echo(
            f"\nThe settings are contained in {click.style(get_settings_path(), bold=True)}"
        )
        return

    if not ctx.invoked_subcommand:
        if not does_file_exist(get_settings_path()):
            click.confirm(
                "Unable to find the settings file. Would you like to start setup",
                prompt_suffix="? ",
                default="Y",
                abort=True,
            )
            setup()
        new()


## CLI commands


@click.option(
    "--editor",
    prompt=click.style(
        "Specify the command that opens your favorite editor", bold=True
    ),
    help="Command that fires up your favorite text editor",
)
@click.option(
    "--posts",
    prompt=click.style("Specify the folder that contains the posts", bold=True),
    type=click.Path(),
    help="Folder that contains your journal entries as markdown files.",
)
@click.option(
    "--serve",
    prompt=click.style(
        "Specify the command that allows you to serve your journal", bold=True
    ),
    type=click.STRING,
    help="Command that allows you to serve your journal. Typically something like `cd myjournal; bundle exec jekyll serve`"
    " where `myjournal` is the folder where your `jekyll` powered site resides.",
    default="",
)
@cli.command()
def setup(editor, posts, serve):
    """Configure the app to manage your markdown based journal"""

    settings = {"posts": posts, "editor": editor, "serve": serve}

    # Adding support for OSX's "~" for home directory
    if posts.startswith("~"):
        settings["posts"] = posts.replace("~", os.environ["HOME"])

    create_settings(settings)


@click.argument("search_term", type=click.STRING, required=True)
@cli.command()
def search(search_term):
    """Allows you to search the journal. Relies on `grep`."""
    # Uses `grep` to search the journal entries
    # Based on https://stackoverflow.com/a/11210185/970897 and http://docs.python.org//glossary.html#term-eafp
    settings = get_settings()

    try:
        # FIXME: In OSX, the message "grep: No such file or directory" always appears even
        # if there are matches. This shouldn't happen. Also, it would be nice to have an
        # explicit message stating that no results were found for a search term.
        cmd_list = ["grep", search_term, os.path.join(settings["posts"], "*.md")]
        exit_code = call(cmd_list)
        if exit_code == 2:
            from glob import glob

            *first, pattern = cmd_list
            call(first + glob(pattern))
    except Exception as e:
        print(
            "Something went wrong while trying to call grep. It is probably not installed. Please follow instructions from https://www.poftut.com/how-to-download-install-and-use-gnu-grep-on-windows/ for Windows."
        )
        print(f"Error message for pros: {e}")


@cli.command()
def serve():
    """Serves your blog at localhost:4000.

    TODO: Add options to fiddle with the port
    """
    import subprocess

    settings = get_settings()

    commands = settings["serve"].split(";")

    for command_string in commands:
        print(command_string)
        # Adding support for OSX's "~" for home directory
        if "~" in command_string:
            command_string = command_string.replace("~", os.environ["HOME"])
            print(command_string)

        subprocess.run(command_string.split())


@click.option("-m", "--message", required=False, type=click.STRING)
@cli.command()
def push(message):
    """Commits the changes to the posts to Git and pushes them
    to the remote repository"""
    try:
        from git import Repo
        from git.exc import GitCommandError
    except ImportError:
        raise ImportError(
            "Using the 'push' command requires GitPython to be installed."
        )
    from time import time

    settings = get_settings()

    folder = os.path.dirname(settings["posts"])
    repo = Repo(folder)
    if not message:
        message = f"Autocommit at {time()}"
    # Commiting the folder with posts and the one with images
    try:
        click.secho("Adding new files to index", bold=True)
        _ = repo.index.add([settings["posts"], "assets/img"])
        click.secho("Committing changes", bold=True)
        repo.index.commit(message)
        click.secho("Pushing to remote repository", bold=True)
        origin = repo.remote("origin")
        origin.push()
    except GitCommandError as giterror:
        click.secho(
            click.style("FAILED: ", fg="red")
            + f"Unable to commit and push to repo. Actual error message - \n\n {giterror}",
            bold=True,
        )
        sys.exit(1)

    click.secho(
        click.style("SUCCESS: ", fg="green")
        + "Updated the journal on remote repository.",
        bold=True,
    )


@cli.command()
def pull():
    """Pulls the latest commits from the remote repo"""
    try:
        from git import Repo
        from git.exc import GitCommandError
    except ImportError:
        raise ImportError(
            "Using the 'push' command requires GitPython to be installed."
        )

    settings = get_settings()

    folder = os.path.dirname(settings["posts"])
    repo = Repo(folder)
    click.secho("Pulling changes from remote repository", bold=True)
    try:
        origin = repo.remote("origin")
        origin.pull()
        click.secho(
            click.style("SUCCESS: ", fg="green") + "Updated the offline journal.",
            bold=True,
        )
    except GitCommandError as giterror:
        click.secho(
            click.style("FAILED: ", fg="red")
            + f"Unable to pull from repo. Actual error message - \n\n {giterror}",
            bold=True,
        )


@click.option(
    "-l",
    "--layout",
    required=False,
    type=click.STRING,
    default="post",
    help="Specify the layout of your entry.",
)
@click.option(
    "-c",
    "--category",
    required=False,
    type=click.STRING,
    default="journal",
    help="Specify the category of the new entry. Typically, it is 'journal'.",
)
@click.option(
    "-t",
    "--title",
    required=False,
    type=click.STRING,
    default=None,
    help="Specify the title of the new entry. A default title based on the date will be assigned if not specified.",
)
@cli.command()
def new(title, category, layout):
    """Creates a new post for the day if one hasn't already
    been created. Opens that day's post in the configured editor
    in case it already exists"""

    settings = get_settings()
    posts = os.listdir(settings["posts"])
    editor_exe = settings["editor"]

    latest = max(posts)  # TODO: Test this :D
    todays_post = get_post_name()
    new_post = os.path.join(settings["posts"], todays_post)

    if todays_post in posts and category is "journal":
        # FIXME: This assumes that the naming convention for the file will always
        # follow the default. This need not be true as Jekyll only cares about the
        # date itself. The correct check would be to first check the date and then *confirm*
        # that the post type is "journal". The latter is necessary because there might be
        # an "essay" written on the same day.

        # This will be a warning
        warnings.warn("Today's journal entry already exists. Opening in text editor.")
    else:
        # Filling in the default header
        # TODO: Make this configurable via a template
        if title is None:
            if todays_post in posts:
                # TODO: Test this portion
                assert os.path.isfile(
                    new_post
                ), "Today's post 'exists' in 'posts' but the file isn't there!"

                raise ValueError(
                    f"The file named {new_post} already exists. If you intended to create an entry that "
                    "is not the standard journal entry, please provide a title explicitly by using the --title option."
                )

            title = get_post_name(day_format="", date_format="MMMM Do", sep="", ext="")

        else:
            new_post = os.path.join(
                settings["posts"], get_post_name(name=title.lower().replace(" ", "-"))
            )

        lines = [
            "---",
            f"title: {title}",
            f"layout: {layout}",
            f"category: {category}",
            "---",
        ]
        template = "\n".join(lines)
        with open(new_post, "w") as file:
            file.write(template)

    call([editor_exe, new_post])


@cli.command()
def previous():
    """Opens the penultimate post, typically "yesterday's" post
    in the configured editor"""
    settings = get_settings()
    posts = os.listdir(settings["posts"])
    editor_exe = settings["editor"]

    penultimate = sorted(posts)[-2]
    penultimate = os.path.join(settings["posts"], penultimate)
    call([editor_exe, penultimate])


@cli.command()
def provoke():
    """Poses a thought provoking question from Edge.org's archives
    and an answer to that question by an expert
    """
    from .edge import provoke

    result = provoke()
    header = (
        click.style(result.question + "\n", fg="red")
        + click.style(result.url + "\n", fg="blue")
        + click.style(result.title + "\n", bold=True)
    )
    click.echo_via_pager(header + result.content)


if __name__ == "__main__":
    cli()
