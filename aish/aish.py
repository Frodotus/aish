import argparse
import json
import os
import re

import requests
from distro import name as distro_name
from rich import print as pprint
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Initializing console object for better user experience and output formatting
console = Console()

user_shell = os.environ["SHELL"].split("/")[-1]
user_distro = distro_name(pretty=True)

DEFAULT_CONFIG = {
    "roles": {
        "default": f"You are a command-line application designed to assist with coding and system management tasks. Your current task is to administer the {user_distro} operating system using the {user_shell} shell. Please only present simple, unformatted text in your responses. Avoid offering any advice or details about your functions.",
        "shell": f"Output only plain text {user_shell} commands for {user_distro}  without any description or explanation. If there is a lack of details, provide the most logical solution. Ensure that the output of your response is a valid shell command. If multiple steps are required, try to combine them together.",
        "code": "Output only plain text code without any description or explanation. Do not ask for more details. If multiple steps are required, try to combine them together.",
    },
    "model": "gpt-3.5-turbo",
    "temperature": 0.5,
    "top_p": 0.5,
    "timeout": 60,
    "role": "default",
    "url": "https://api.openai.com/v1/chat/completions",
}


def load_config(defaults):
    try:
        with open("config.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = defaults
    defaults.update(config)
    return defaults


def execute_shell_commands(commands, debug=False):
    shell = os.environ.get("SHELL", "/bin/sh")
    if debug:
        print("Commands: ", commands)

    if len(commands) > 0:
        for command in commands:
            choice = input(f"Execute command '{command}'? (Y/n): ")

            if choice.lower() == "y" or choice == "":
                os.system(f"{shell} -c '{command}'")


def get_api_response(data, headers, config, debug=False):
    with requests.post(
        config["url"],
        headers=headers,
        data=json.dumps(data),
        timeout=config["timeout"],
        stream=True,
    ) as response:
        response.raise_for_status()
        answer = ""
        rline = ""

        in_code_block = False
        language = ""
        lines_printed = 0
        for line in response.iter_lines():
            data = line.lstrip(b"data: ").decode("utf-8")
            if data == "[DONE]":
                console.print("", end="\r")

                if "```" in rline:
                    in_code_block = not in_code_block
                    rline = "   "

                if in_code_block:
                    syntax = Syntax(rline, language)
                    console.print(syntax, end="\n")
                else:
                    if lines_printed == 0 and config["role"] == "shell":
                        syntax = Syntax(rline, language)
                        console.print(syntax, end="\n")
                        if not re.search("this is not a .* command\.", rline):
                            answer = f"```\n{rline}\n```"
                    else:
                        console.print(rline, end="\n")

                rline = ""
                break

            if not data:
                continue

            data = json.loads(data)
            delta = data["choices"][0]["delta"]
            if "content" not in delta:
                continue
            answer += delta["content"]
            out = delta["content"]

            if "\n" in out:
                lines_printed += 1
                out = out.replace("\n", "")
                rline += out

                console.print("", end="\r")

                if "```" in rline:
                    console.print("            ", end="\n")
                    in_code_block = not in_code_block
                    if in_code_block:
                        parts = rline.split("```")
                        if len(parts) > 1:
                            language = parts[1]
                        else:
                            language = user_shell
                    rline = ""

                elif in_code_block:
                    syntax = Syntax(rline, language)
                    console.print(syntax, end="\n")
                else:
                    console.print(rline, end="\n")
                rline = ""
            else:
                console.print(out, end="")
                rline += out

        print()

        if config["role"] == "shell":
            code_blocks = []
            lines = answer.split("\n")
            in_code_block = False

            for line in lines:
                if "```" in line:
                    in_code_block = not in_code_block
                elif in_code_block:
                    code_blocks.append(line.strip())

            execute_shell_commands(code_blocks, debug)


def chat(prompt, config, debug=False, playback=False):
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

    if playback:
        data["playback"] = True

    if debug:
        pprint("--- Request ---")
        pprint(data)
        pprint("--- Response ---")

    get_api_response(data, headers, config, debug)


def main():
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
        help="The maximum time in seconds that the request will wait for a response from the API.",
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
        "-b",
        action="store_true",
        help="Replay the conversation from the beginning.",
    )

    args = parser.parse_args()
    config = load_config(DEFAULT_CONFIG)

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

    try:                                                                                                                                                                                                                        
        chat(args.prompt, config, args.debug, args.playback)
    except KeyboardInterrupt:                                                                                                                                                                                                   
        pass



if __name__ == "__main__":
    main()
