# Importing necessary libraries
import argparse
import json
import os

import requests
from rich import print as pprint
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

# Initializing console object for better user experience and output formatting
console = Console()


# Initializing the chat function with default parameters and/or custom configurations
def chat(
    prompt, model, temperature, top_p, timeout, role, url, debug=False, playback=False
):
    defaults = {
        "roles": {
            "default": "You are a command-line application designed to assist with coding and system management tasks. Your current task is to administer the Mac OS operating system using the zsh shell. Please only present simple, unformatted text in your responses. Avoid offering any advice or details about your functions.",
            "shell": "Output only plain text zsh commands for Mac OS  without any description or explanation. If there is a lack of details, provide the most logical solution. Ensure that the output of your response is a valid shell command. If multiple steps are required, try to combine them together.",
            "code": "Output only plain text code without any description or explanation. Do not ask for more details. If multiple steps are required, try to combine them together.",
        },
        "model": "gpt-3.5-turbo",
        "temperature": 0.5,
        "top_p": 0.5,
        "timeout": 60,
        "role": "default",
        "url": "https://api.openai.com/v1/chat/completions",
    }

    # Reading the configuration from a config.json file, and overriding any attribute if provided by the user
    try:
        with open("config.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        config = defaults
    defaults.update(config)
    model = model or defaults["model"]
    temperature = temperature or defaults["temperature"]
    top_p = top_p or defaults["top_p"]
    timeout = timeout or defaults["timeout"]
    role = role or defaults["role"]
    url = url or defaults["url"]
    prompt = prompt or []

    # Role validation
    if role not in defaults["roles"]:
        print(
            f"Error: '{role}' is not a valid role. Please choose from: {list(defaults['roles'].keys())}"
        )
        return

    # Formatting user input and preparing headers for requesting chat(Response formatting)
    prompt = " ".join(prompt)
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }

    # Configuration setup for the request
    messages = [
        {"role": "system", "content": defaults["roles"][role]},
        {"role": "user", "content": prompt},
    ]
    data = {
        "messages": messages,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "stream": True,
    }

    # Enabling playback feature if requested by user for the previous response
    if playback:
        data["playback"] = True

    # Debugging enabled to display the request and response details
    if debug:
        pprint("--- Request ---")
        pprint(data)
        pprint("--- Response ---")

    # Making the API call to OpenAI GPT-3 Chat API
    with requests.post(
        url, headers=headers, data=json.dumps(data), timeout=timeout, stream=True
    ) as response:
        response.raise_for_status()
        answer = ""
        rline = ""

        in_code_block = False
        language = ""

        # Iterating through the response received in chunks of lines
        for line in response.iter_lines():
            # Converting the byte output to string and checking if response is completely received
            data = line.lstrip(b"data: ").decode("utf-8")
            if data == "[DONE]":
                console.print("", end="\r")
                if "```" in rline:  # This line is a delimiter
                    in_code_block = not in_code_block  # Change the state
                    rline = "   "

                if in_code_block:
                    console.print(Panel(rline), end="\n")
                else:
                    console.print(rline, end="\n")
                    
                rline = ""
                break

            # Checking if response is empty after decoding, useful for handling exceptions
            if not data:
                continue

            # Extracting the content to display from the JSON response
            data = json.loads(data)
            delta = data["choices"][0]["delta"]
            if "content" not in delta:
                continue
            answer += delta["content"]
            out = delta["content"]
            # Handling multiple lines of output formatting with Rich library
            if "\n" in out:
                out = out.replace("\n", "")
                rline += out

                console.print("", end="\r")
                    
                if "```" in rline:  # This line is a delimiter
                    in_code_block = not in_code_block
                    if in_code_block:
                        # Split the line by "```"
                        parts = rline.split("```")
                        if len(parts) > 1:
                            # The second part of the split contains the language
                            language = parts[1]
                        else:
                            # No language specified
                            language = "zsh"
                    else:
                        console.print("           ", end="\r")
                    rline = ""

                if in_code_block:
                    syntax = Syntax(rline, language)
                    console.print(syntax, end="\n")
                else:
                    console.print(rline, end="\n")
                rline = ""
            else:
                console.print(out, end="")
                rline += out

        print()

        # Processing code blocks obtained from response for shell role
        if role == "shell":
            shell = os.environ.get("SHELL", "/bin/sh")
            code_blocks = []
            lines = answer.split("\n")
            in_code_block = False

            for line in lines:
                if "```" in line:  # This line is a delimiter
                    in_code_block = not in_code_block  # Change the state
                elif in_code_block:  # We're inside a code block
                    code_blocks.append(line.strip())

            # Printing the resulting lines
            if debug:
                print("Commands: ", code_blocks)

            if len(code_blocks) > 0:
                # Loop through each command in the list
                for code_block in code_blocks:
                    commands = code_block.split("\n")
                    for command in commands:
                        choice = input(f"Execute command '{command}'? (Y/n): ")

                        # If the user selects yes, execute the current command
                        if choice.lower() == "y" or choice == "":
                            os.system(f"{shell} -c '{command}'")


def main():
    # Initializing ArgumentParser object with description of chat function arguments
    parser = argparse.ArgumentParser(description="Get a response from the ChatGPT API.")
    parser.add_argument(
        "prompt", nargs="*", help="The initial text that you want the AI to respond to."
    )
    parser.add_argument(
        "--model", type=str, help="The model version that you want to use."
    )
    parser.add_argument(
        "--temperature", type=float, help="The randomness of the AI’s responses."
    )
    parser.add_argument(
        "--top_p", type=float, help="A parameter for controlling randomness."
    )
    parser.add_argument(
        "--timeout",
        type=int,
        help="The maximum time in seconds that the request will wait for a response from the API.",
    )
    parser.add_argument("--role", type=str, help="The role of the assistant.")
    parser.add_argument(
        "--shell", "-s", action="store_true", help="Execute the command in the shell."
    )
    parser.add_argument("--code", "-c", action="store_true", help="Output only code.")
    parser.add_argument("--url", type=str, help="The API endpoint to use.")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument(
        "--playback",
        action="store_true",
        help="Playback previous response. Works only when using proxy",
    )

    args = parser.parse_args()
    role = args.role or "default"

    # Setting the role based on user parameters code or shell
    if args.code:
        role = "code"
    elif args.shell:
        role = "shell"

    # Calling the chat function with all the parameters
    chat(
        args.prompt,
        args.model,
        args.temperature,
        args.top_p,
        args.timeout,
        role,
        args.url,
        debug=args.debug,
        playback=args.playback,
    )


if __name__ == "__main__":
    main()
