"""Journaling from the command line

Features:-

1. journal new - Find the folder where your posts live (based on a settings file)
and creates a new blank journal entry. If a post for the current day already exists,
it gives an error and opens the existing file in a command line interface of your
choice.

2. journal yesterday - Opens the previous post

3. journal setup - Create a settings file from scratch

4. journal search SEARCH_TERM - Search all posts using GNU grep
"""

import os
import json
import warnings
import click
from pathlib import Path
import typing as t
import sys
from subprocess import call

COMMANDS = {"new", "yesterday", "search", "setup", "push"}
SETTINGS_FILE = "settings.json"


def check_platform():
    """Function that raises an error if the platform is not Windows."""
    import sys

    # Check if platform is Windows
    if sys.platform != "win32":
        raise NotImplementedError("We support only Windows currently.")


def does_file_exist(filepath: str) -> bool:
    """Helper function that checks whether the file exists"""
    my_file = Path(filepath)
    return my_file.is_file()


def get_settings_path() -> str:
    """Returns the full path of the settings file"""
    # TODO: Support for other OSes, right now APPDATA path is
    # hardcoded
    folder_path = os.path.join(os.environ["APPDATA"], "journal")
    file_path = os.path.join(folder_path, SETTINGS_FILE)
    return file_path


def get_settings() -> t.Dict[str, str]:
    """Function that returns the settings as a dict"""
    config = get_settings_path()
    if not does_file_exist(config):
        raise OSError(f"Settings file not found at {config}")
    with open(config, "r") as f:
        settings = json.load(f)
    return settings


def create_settings(data: t.Dict[str, str]) -> None:
    """Creates a SETTINGS_FILE file that stores configuration info"""
    file_path = get_settings_path()

    if does_file_exist(file_path):
        raise ValueError(f"The settings file already exists at {file_path}")

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
):
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


@click.option("--config", is_flag=True, help="Displays the current settings.")
@click.argument("search_term", type=click.STRING, required=False)
@click.argument(
    "command",
    type=click.Choice(COMMANDS),
    default="new",
)
@click.command()
def cli(command, search_term, config):
    """Welcome to Journal CLI.

    The command is a string that is equal to one of {new, yesterday, setup}.
    """

    settings = get_settings()
    posts = os.listdir(settings["posts"])
    editor_exe = settings["editor"]

    if config:
        # TODO: Beautify the stdout
        print(settings)
        return

    if command == "push":
        # Commits the changes to the posts to Git and pushes them
        # to the remote repository
        try:
            from git import Repo
        except ImportError:
            raise ImportError(
                "Using the 'push' command requires GitPython to be installed."
            )
        from time import time
        # import pdb; pdb.set_trace()
        folder = os.path.dirname(settings["posts"])
        repo = Repo(folder)
        commit_msg = f"Autocommit at {time()}"
        # Commiting the folder with posts and the one with images
        _ = repo.index.add([settings["posts"], 'assets/img'])
        repo.index.commit(commit_msg)
        origin = repo.remote('origin')
        origin.push()
        print("Sucessfully updated the journal on remote repository.")

    elif command == "new":
        latest = max(posts)  # TODO: Test this :D
        todays_post = get_post_name()
        new_post = os.path.join(settings["posts"], todays_post)

        if latest == todays_post:
            # This will be a warning
            warnings.warn("Today's post already exists. Opening in text editor.")
        else:
            # Filling in the default header
            # TODO: Make this configurable via a template
            title = get_post_name(day_format="", date_format="MMMM Do", sep="", ext="")
            lines = [
                "---",
                f"title: {title}",
                "layout: post",
                "category: journal",
                "---",
            ]
            template = "\n".join(lines)
            with open(new_post, "w") as file:
                file.write(template)

        call([editor_exe, new_post])

    elif command == "yesterday":
        # Gets the penultimate post, typically "yesterday's" post
        penultimate = sorted(posts)[-2]
        penultimate = os.path.join(settings["posts"], penultimate)
        call([editor_exe, penultimate])

    elif command == "search":
        # Uses `grep` to search the journal entries
        # Based on https://stackoverflow.com/a/11210185/970897 and http://docs.python.org//glossary.html#term-eafp
        if not search_term:
            click.echo("Please enter a search term.")
            sys.exit(1)

        try:
            call(["grep", search_term, os.path.join(settings["posts"], "*.md")])
        except Exception as e:
            print(
                "Something went wrong while trying to call grep. It is probably not installed. Please follow instructions from https://www.poftut.com/how-to-download-install-and-use-gnu-grep-on-windows/ for Windows."
            )
            print(f"Error message for pros: {e}")

    elif command == "setup":
        from PyInquirer import style_from_dict, Token, prompt, Separator

        style = style_from_dict(
            {
                Token.Separator: "#cc5454",
                Token.QuestionMark: "#673ab7 bold",
                Token.Selected: "#cc5454",  # default
                Token.Pointer: "#673ab7 bold",
                Token.Instruction: "",  # default
                Token.Answer: "#f44336 bold",
                Token.Question: "",
            }
        )
        questions = [
            {
                "type": "input",
                "message": "Enter editor path:",
                "name": "editor",
                # 'validate': lambda answer: 'You must choose at least one topping.'
            },
            {
                "type": "input",
                "message": "Enter path for posts",
                "name": "posts",
            },
        ]

        settings = prompt(questions, style=style)
        create_settings(settings)

    else:
        raise ValueError(f"Argument: `{command}` is not supported.")


if __name__ == "__main__":
    cli()
