import json
import os

from aish import aish


def test_execute_shell_commands(mocker):
    # Define mock inputs and output
    commands = ['echo "hello"', "date"]

    # Define expected prompt message
    prompt_message = "\nExecute command '{}'? (Y/n): "

    # Create a mock for input() function that always returns "yes"
    mocker.patch("builtins.input", return_value="y")

    # Execute the shell commands
    aish.execute_shell_commands(commands)

    # Assert that the prompt message was displayed for each command
    expected = [
        mocker.call(prompt_message.format('echo "hello"')),
        mocker.call(prompt_message.format("date")),
    ]
    assert input.mock_calls == expected


def test_load_config(mocker):
    # Patch the file reading function to return the desired data
    mocker.patch(
        "builtins.open", mocker.mock_open(read_data=json.dumps({"key": "value"}))
    )

    # Test that load_config reads the config from the mocked file and
    # updates the defaults
    defaults = {"key": "default", "key2": "default2"}
    result = aish.load_config(defaults)
    assert result == {"key": "value", "key2": "default2"}

    # Test that load_config falls back to defaults if the file doesn't exist
    m = mocker.mock_open()
    m.side_effect = FileNotFoundError
    mocker.patch("builtins.open", m)
    result = aish.load_config(defaults)
    assert result == defaults


def test_get_code_blocks():
    # Test that the function handles nested code blocks correctly
    answer = (
        "Here is some text\n"
        "```\n"
        "echo 'This **is** a code block'\n"
        "```\n"
        "Even more text\n"
    )
    config = {"role": "shell"}
    expected_output = ["echo 'This **is** a code block'"]
    assert aish.get_code_blocks(answer, config) == expected_output

    # Test that the function returns an empty list when no code blocks are present
    answer = "Here is some text\nwith no code blocks\nor backticks"
    config = {"role": "shell"}
    expected_output = []
    assert aish.get_code_blocks(answer, config) == expected_output

    # Test that the function does not extract code blocks when the role is default
    answer = "Here is some text\n```\necho 'Hello, world!'\n```\nMore text"
    config = {"role": "default"}
    expected_output = []
    assert aish.get_code_blocks(answer, config) == expected_output

    # Test that the function does not extract code blocks when the role is code
    answer = (
        "Here is some text\n"
        "```python\necho 'Hello, world!'\n"
        "```\n"
        "More text\n"
        "```python\n"
        "x = 1\n"
        "y = 2\n"
        "z = x + y\n"
        "print(z)\n"
        "```\n"
        "Even more text"
    )
    config = {"role": "shell"}
    expected_output = []
    assert aish.get_code_blocks(answer, config) == expected_output

    # Test that oneliner is extracted correctly
    answer = "echo 'Hello, world!'"
    config = {"role": "shell"}
    expected_output = ["echo 'Hello, world!'"]
    assert aish.get_code_blocks(answer, config) == expected_output


def test_process_delta(capsys):
    test_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_responses",
    )
    with open(os.path.join(test_dir, "oneliner.txt"), "r") as f:
        lines = f.readlines()
        result = ""
        for line in lines:
            data = line.lstrip("data: ")
            result += aish.process_delta(data, result)
    captured = capsys.readouterr()
    expected_output = "\ntest1\rtest1\rtest1\r"
    assert expected_output == captured.out

    with open(os.path.join(test_dir, "codeblock_short.txt"), "r") as f:
        lines = f.readlines()
        result = ""
        for line in lines:
            data = line.lstrip("data: ")
            result += aish.process_delta(data, result)
    print("->", captured.out)
    captured = capsys.readouterr()
    expected_output = "\ntest1\rtest1:\n``\r            \ntest2\rtest2\n``\r            \ntest3\rtest3:\n``\r            \ntest4\rtest4\n            \n            \n```test5\r            \n-> \ntest1\rtest1\rtest1\r\n"
    assert expected_output == captured.out

    with open(
        os.path.join(test_dir, "codeblock_ends_at_last_line_short.txt"), "r"
    ) as f:
        lines = f.readlines()
        result = ""
        for line in lines:
            data = line.lstrip("data: ")
            result += aish.process_delta(data, result)
    captured = capsys.readouterr()
    expected_output = "\n            \n  \r   python\r   python setup\r   python setup.py\r   python setup.py b\r   python setup.py bdist\r   python setup.py bdist_wheel\r   python setup.py bdist_wheel\n  \r            \n  ```\r            \n"
    assert expected_output == captured.out

    with open(os.path.join(test_dir, "not_command.txt"), "r") as f:
        lines = f.readlines()
        result = ""
        for line in lines:
            data = line.lstrip("data: ")
            result += aish.process_delta(data, result)
    captured = capsys.readouterr()
    expected_output = "\nTest\rTest.\rTest. However\rTest. However,\rTest. However, this\rTest. However, this is\rTest. However, this is not\rTest. However, this is not a\rTest. However, this is not a z\rTest. However, this is not a zsh\rTest. However, this is not a zsh command\rTest. However, this is not a zsh command for\rTest. However, this is not a zsh command for Darwin\rTest. However, this is not a zsh command for Darwin \rTest. However, this is not a zsh command for Darwin 22\rTest. However, this is not a zsh command for Darwin 22.\rTest. However, this is not a zsh command for Darwin 22.4\rTest. However, this is not a zsh command for Darwin 22.4.\rTest. However, this is not a zsh command for Darwin 22.4.0\rTest. However, this is not a zsh command for Darwin 22.4.0.\rTest. However, this is not a zsh command for Darwin 22.4.0.\rTest. However, this is not a zsh command for Darwin 22.4.0.\r"
    assert expected_output == captured.out


# python_code.txt
