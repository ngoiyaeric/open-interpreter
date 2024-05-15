import os
import json
import time
from typing import List, TypedDict

import pkg_resources
import requests

from interpreter.terminal_interface.profiles.profiles import write_key_to_profile
from interpreter.terminal_interface.utils.display_markdown_message import display_markdown_message


contribute_cache_path = os.path.join(
    os.path.expanduser("~"), ".cache", "open-interpreter", "contribute.json"
)


def display_contribution_message():
    display_markdown_message(
"""
---
> We're training an open-source language model!

You can help us train it with your past, current, or future conversations by:
1. Closing out of OpenInterpreter,
2. Running `interpreter --contribute_conversation`.
"""
    )
    time.sleep(1)


def display_contributing_current_message():
    display_markdown_message(
f"""
---
> This conversation will be used to train OpenInterpreter's language model.
"""
    )


def send_past_conversations(interpreter):
    past_conversations = get_all_conversations(interpreter)
    if len(past_conversations) > 0:
        print()
        print("Sending all previous conversations to OpenInterpreter...")
        contribute_conversations(past_conversations)
        print()


def set_send_future_conversations(interpreter, should_send_future):
    write_key_to_profile("contribute_conversation", should_send_future)
    display_markdown_message(
"""
> OpenInterpreter will contribute all your conversations from now on.

To change this, consult the documentation at [https://unassuminglink.com](https://www.readthefuckingmanual.com).
"""
    )


def user_wants_to_contribute_past():
    print("Would you like to contribute all past conversations?")
    response = input("(y/n) ")
    return response.lower() == "y"


def user_wants_to_contribute_future():
    print("Would you like to contribute all future conversations?")
    response = input("(y/n) ")
    return response.lower() == "y"


def contribute_conversation_launch_logic(interpreter):
    contribution_cache = get_contribute_cache_contents()

    if interpreter.will_contribute:
        contribute_past_and_future_logic(interpreter, contribution_cache)
    elif not contribution_cache["displayed_contribution_message"]:
        display_contribution_message()

    # don't show the contribution message again no matter what.
    contribution_cache["displayed_contribution_message"] = True
    write_to_contribution_cache(contribution_cache)


class ContributionCache(TypedDict):
    displayed_contribution_message: bool
    asked_to_contribute_past: bool
    asked_to_contribute_future: bool


# modifies the contribution cache!
def contribute_past_and_future_logic(
    interpreter, contribution_cache: ContributionCache
):
    if not contribution_cache["asked_to_contribute_past"]:
        if user_wants_to_contribute_past():
            send_past_conversations(interpreter)
        contribution_cache["asked_to_contribute_past"] = True

    if not contribution_cache["asked_to_contribute_future"]:
        if user_wants_to_contribute_future():
            set_send_future_conversations(interpreter, True)
        contribution_cache["asked_to_contribute_future"] = True

    display_contributing_current_message()


# Returns a {"asked_to_run_contribute": bool, "asked_to_contribute_past": bool}
# as the first part of its Tuple, a bool as a second.
# Writes the contribution cache file if it doesn't already exist.
# The bool is True if the file does not already exist, False if it does.
def get_contribute_cache_contents() -> ContributionCache:
    if not os.path.exists(contribute_cache_path):
        default_dict: ContributionCache = {
            "asked_to_contribute_past": False,
            "displayed_contribution_message": False,
            "asked_to_contribute_future": False,
        }
        with open(contribute_cache_path, "a") as file:
            file.write(json.dumps(default_dict))
        return default_dict
    else:
        with open(contribute_cache_path, "r") as file:
            contribute_cache = json.load(file)
            return contribute_cache


# Takes in a {"asked_to_run_contribute": bool, "asked_to_contribute_past": bool}
def write_to_contribution_cache(contribution_cache: ContributionCache):
    with open(contribute_cache_path, "w") as file:
        json.dump(contribution_cache, file)


def get_all_conversations(interpreter) -> List[List]:
    def is_conversation_path(path: str):
        _, ext = os.path.splitext(path)
        return ext == ".json"

    history_path = interpreter.conversation_history_path
    all_conversations: List[List] = []
    conversation_files = os.listdir(history_path) if os.path.exists(history_path) else []
    for mpath in conversation_files:
        if not is_conversation_path(mpath):
            continue
        full_path = os.path.join(history_path, mpath)
        with open(full_path, "r") as cfile:
            conversation = json.load(cfile)
            all_conversations.append(conversation)
    return all_conversations


def is_list_of_lists(l):
    return isinstance(l, list) and all([isinstance(e, list) for e in l])


def contribute_conversations(conversations: List[List]):
    if len(conversations) == 0 or len(conversations[0]) == 0:
        return None

    url = "https://api.openinterpreter.com/v0/conversations/contribute/"
    version = pkg_resources.get_distribution("open-interpreter").version

    payload = {"conversations": conversations, "oi_version": version}

    assert is_list_of_lists(payload["conversations"]), "the contribution payload is not a list of lists!"

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            print(
                f"Failed to contribute conversation: {response.status_code} {response.text}"
            )
            return None
        else:
            print(f"Successfully contributed conversations!")
    except requests.RequestException as e:
        print(f"Failed to contribute conversation: {e}")
        return None
