import argparse
import json
import os
import re

import requests
from distro import name as distro_name
from rich import print as pprint
from rich.console import Console
from rich.syntax import Syntax

# Initializing console object for output formatting
console = Console()

debug = False

user_shell = os.environ["SHELL"].split("/")[-1]
user_distro = distro_name(pretty=True)

DEFAULT_CONFIG = {
    "roles": {
        "default": f"You are a command-line application designed to assist with "
        f"coding and system management tasks. Your current task is to "
        f"administer the {user_distro} operating system using the "
        f"{user_shell} shell. Please only present simple, unformatted "
        f"text in your responses. Avoid offering any advice or details "
        f"about your functions.",
        "shell": f"Output only plain text {user_shell} commands for {user_distro} "
        f"without any description or explanation. If there is a lack of "
        f"details, provide the most logical solution. Ensure that the "
        f"output of your response is a valid shell command. If multiple "
        f"steps are required, try to combine them together.",
        "code": "Output only plain text code without any description or explanation. "
        "Do not ask for more details. If multiple steps are required, "
        "try to combine them together.",
    },
    "model": "gpt-3.5-turbo",
    "temperature": 0.5,
    "top_p": 0.5,
    "timeout": 60,
    "role": "default",
    "url": "https://api.openai.com/v1/chat/completions",
}


def load_config(defaults):
    """
    This function takes a dictionary of default configuration settings and loads any
    additional settings from a 'config.json' file, if it exists. If the file does not
    exist, only the default settings are used.

    :param defaults: Dictionary containing default configuration settings.
    :type defaults: dict

    :return: Dictionary containing all configuration settings.
    :rtype: dict
    """

    try:
        with open("config.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = defaults
    defaults.update(config)
    return defaults


def execute_shell_commands(commands):
    """
    Executes a list of shell commands.

    Args:
        commands: A list of shell commands to execute.
    """

    shell = os.environ.get("SHELL", "/bin/sh")
    if debug:
        print("Commands: ", commands)

    if len(commands) > 0:
        for command in commands:
            choice = input(f"\nExecute command '{command}'? (Y/n): ")

            if choice.lower() == "y" or choice == "":
                os.system(f"{shell} -c '{command}'")


def process_response(response, config):
    """
    Extracts and processes response from a remote server.

    Args:
        response: A requests.Response object containing the response from the
                  remote server.
        config: A dictionary containing configuration information.

    Returns:
        The answer as a string.
    """

    global user_shell
    answer = ""

    for line in response.iter_lines():
        data = line.lstrip(b"data: ").decode("utf-8")

        if not data:
            continue

        answer = process_delta(data, answer)

    return answer


def process_delta(data, answer):
    """
    Extracts and processes response from a remote server.

    Args:
        response: A requests.Response object containing the response from the
                  remote server.
        config: A dictionary containing configuration information.

    Returns:
        The answer as a string.
    """

    global user_shell

    try:
        language = ""
        data = json.loads(data)
        delta = data["choices"][0]["delta"]
        finish_reason = data["choices"][0]["finish_reason"]
        chunk = ""
        if "content" in delta:
            answer += delta["content"]
            chunk = delta["content"]
        elif finish_reason:
            if answer.count("\n") == 1:
                ll = answer.split("\n")[-1]
                if not re.search("this is not a .* command.", ll):
                    answer = f"```\n{ll}\n```"
                    chunk = "```"
                    syntax = Syntax(ll, language)
                    console.print(syntax, end="\n")
                else:
                    console.print(ll, end="\n")
            else:
                ll = answer.split("\n")[-1]
                console.print(ll, end="\r")
                pass
        else:
            answer += "\n"
            chunk = "\n"
        count = answer.count("```")
        last_line = answer.split("\n")[-1]
        in_code_block = count % 2 == 1

        line_ends = chunk.count("\n")
        if line_ends > 0 or "```" in last_line:
            last_line = answer.split("\n")[-1 - line_ends]
            if "```" in last_line:
                # TODO: Handle language printout
                console.print("            ", end="\n")
                if in_code_block:
                    parts = last_line.split("```")
                    if len(parts) > 1:
                        language = parts[1]
                    else:
                        language = user_shell

            elif in_code_block:
                syntax = Syntax(last_line, language)
                console.print(syntax, end="\n")
            else:
                console.print(last_line, end="\n")
        else:
            console.print(last_line, end="\r")
    except json.decoder.JSONDecodeError:
        pass

    return answer


def get_code_blocks(answer, config):
    """
    Extracts code blocks from a response.

    Args:
        answer: A string containing the response from the remote server.
        config: A dictionary containing configuration information.

    Returns:
        A list of code blocks.
    """

    code_blocks = []
    if config["role"] == "shell":
        lines = answer.split("\n")

        if len(lines) == 1:
            code_blocks.append(lines[0].strip())
        else:
            in_code_block = False
            is_block_start = False
            for line in lines:
                has_triple_backtick = "```" in line
                if has_triple_backtick:
                    is_block_start = not is_block_start
                    index = line.index("```") + 3
                    code_block_indicator = line[index:].strip()

                    if is_block_start and (
                        code_block_indicator == user_shell or code_block_indicator == ""
                    ):
                        in_code_block = True
                    else:
                        in_code_block = False
                elif in_code_block:
                    code_blocks.append(line.strip())

    return code_blocks


def get_api_response(data, headers, config):
    """
    Sends a POST request to a remote server using the provided data and headers,
    then processes the response and executes any shell commands.

    Args:
        data: A dictionary containing the data to be sent in the request body.
        headers: A dictionary containing the headers to be sent with the request.
        config: A dictionary containing configuration information.

    Returns:
        None.
    """

    with requests.post(
        config["url"],
        headers=headers,
        data=json.dumps(data),
        timeout=config["timeout"],
        stream=True,
    ) as response:
        response.raise_for_status()

        answer = process_response(response, config)
        code_blocks = get_code_blocks(answer, config)
        execute_shell_commands(code_blocks)


def chat(prompt, config, record=None, playback=None):
    """
    This function takes a prompt, configuration dictionary, and optional playback
    arguments. It sends a request to the OpenAI API to generate a response to the
    prompt using the specified model, temperature, and top_p values from the
    configuration. The response is returned as an output.

    :param prompt: A list of prompts for the chatbot.
    :type prompt: list

    :param config: Configuration dictionary used by the chatbot.
    :type config: dict

    :param playback: A file containing the conversation to be replayed.
    :type playback: str

    :return: Response generated by the chatbot API.
    :rtype: JSON object
    """

    prompt = " ".join(prompt)
    if prompt == "":
        prompt = input("How can I help you? ")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }

    messages = [
        {"role": "system", "content": config["roles"][config["role"]]},
        {"role": "user", "content": prompt},
    ]
    data = {
        "messages": messages,
        "model": config["model"],
        "temperature": config["temperature"],
        "top_p": config["top_p"],
        "stream": True,
    }

    if record:
        data["record"] = record

    if playback:
        data["playback"] = playback

    if debug:
        pprint("--- Request ---")
        pprint(data)
        pprint("--- Response ---")

    get_api_response(data, headers, config)


def main():
    """
    The main function of the program, which is responsible for parsing command-line
    arguments and launching the chatbot with appropriate configuration.
    """

    parser = argparse.ArgumentParser(description="Get a response from the ChatGPT API.")
    parser.add_argument(
        "prompt", nargs="*", help="The initial text that you want the AI to respond to."
    )
    parser.add_argument(
        "--model", "-m", type=str, help="The model version that you want to use."
    )
    parser.add_argument(
        "--temperature", "-t", type=float, help="The randomness of the AI’s responses."
    )
    parser.add_argument(
        "--top_p", "-p", type=float, help="A parameter for controlling randomness."
    )
    parser.add_argument(
        "--timeout",
        "-o",
        type=int,
        help="The maximum time in seconds that the request will wait for a response"
        "from the API.",
    )
    parser.add_argument("--role", "-r", type=str, help="The role of the assistant.")
    parser.add_argument(
        "--shell", "-s", action="store_true", help="Execute the command in the shell."
    )
    parser.add_argument("--code", "-c", action="store_true", help="Output only code.")
    parser.add_argument("--url", "-u", type=str, help="The API endpoint to use.")
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Print debug information to the console.",
    )
    parser.add_argument(
        "--playback",
        type=str,
        help="Replay the conversation from the beginning.",
    )
    parser.add_argument(
        "--record",
        type=str,
        help="Record the conversation to a file.",
    )

    args = parser.parse_args()
    config = load_config(DEFAULT_CONFIG)
    global debug

    if args.model:
        config["model"] = args.model
    if args.temperature:
        config["temperature"] = args.temperature
    if args.top_p:
        config["top_p"] = args.top_p
    if args.timeout:
        config["timeout"] = args.timeout
    if args.role:
        config["role"] = args.role
    if args.url:
        config["url"] = args.url
    if args.code:
        config["role"] = "code"
    elif args.shell:
        config["role"] = "shell"
    debug = args.debug

    try:
        chat(args.prompt, config, args.record, args.playback)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":  # pragma: no cover
    main()
