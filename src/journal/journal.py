"""Journaling from the command line

Features:-

1. journal new - Find the folder where your posts live (based on a settings file)
and creates a new blank journal entry. If a post for the current day already exists,
it gives an error and opens the existing file in a command line interface of your
choice.

2. journal setup - Create a settings file from scratch
"""

import os
import json
import warnings
import click
from pathlib import Path
import typing as t
from subprocess import call

COMMANDS = {"new", "yesterday", "setup"}
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


def get_post_name(name: str = None, date: str = None):
    """Function that generates the filename for a journal post
    written in markdown. It creates a default post name if
    nothing is specified. The post entry refers to today's entry.

    Typically of the format: 2021-01-07-post-name

    TODO: Custom names from CLI
    """
    import arrow

    now = arrow.now()

    if date is None:
        date = now.format("YYYY-MM-DD")
    else:
        raise NotImplementedError("Posts for custom dates not supported yet.")
    if name is None:
        name = now.format("MMMM-D").lower()

    # FIXME: Hardcoding extension may not be a great idea
    return date + "-" + name + ".md"


@click.argument(
    "command",
    type=click.Choice(COMMANDS),
    default="new",
)
@click.command()
def cli(command):
    """Welcome to Journal CLI.
    
    The command is a string that is equal to one of {new, yesterday, setup}.
    """

    settings = get_settings()
    posts = os.listdir(settings["posts"])
    editor_exe = settings["editor"]

    if command == "new":
        latest = max(posts)  # TODO: Test this :D
        todays_post = get_post_name()
        new_post = os.path.join(settings["posts"], todays_post)

        if latest == todays_post:
            # This will be a warning
            warnings.warn("Today's post already exists. Opening in text editor.")
        else:
            # Filling in the default header
            # TODO: Make this configurable via a template
            lines = [
                "---",
                f"title: {todays_post}",
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
                "message": "Enter for posts",
                "name": "posts",
            },
        ]

        settings = prompt(questions, style=style)
        create_settings(settings)

    else:
        raise ValueError(f"Argument: `{command}` is not supported.")


if __name__ == "__main__":
    cli()