# Aish - ChatGPT CLI

This command-line interface (CLI) application is used to interact with the OpenAI through the OpenAI API. The chatbot takes an input prompt and returns a response from the selected model.

## Installation

Ensure you have Python 3.7+ installed. To install the required libraries, use:

```bash
    pip install aish
```

## Usage

To use the application, you need to set the environment variable `OPENAI_API_KEY` with your OpenAI API key. Then, you can run the script from the terminal using the command:

```bash
    aish How can i list all files older than 30 days?
```

```bash
    aish -s How can i list all files older than 30 days?
```

```bash
    aish -c code Write a hello world app in python
```

Optional parameters will take default values if not provided:

- `ModelVersion`: The model version that you want to use. Default is "gpt-3.5-turbo".
- `TemperatureValue`: The randomness of the AI’s responses. A lower value makes the output more focused and deterministic, while higher values produce more diverse and random outputs. Default is 0.5.
- `TopPValue`: A parameter for controlling randomness. A higher value generates more random responses, and a lower value generates more deterministic responses. Default is 0.5.
- `TimeoutValue`: The maximum time in seconds that the request will wait for a response from the API. Default is 60.

## Help

You can display the help message which provides details about the command usage and the different parameters by running:

```bash
    aish --help
```