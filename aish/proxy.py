import json
import os
from time import sleep

import requests
from flask import Flask, Response, request

app = Flask(__name__)

test_dir = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "../",
    "tests/test_responses",
)


@app.route("/api/chat", methods=["POST"])
def proxy():
    """
    This function is a Flask route that listens for POST requests at the '/api/chat'
    endpoint. It acts as a proxy and forwards the incoming request to another server
    for processing. The response received from the server is then returned back to
    the client.

    Method: POST

    Parameters:
    None

    Returns:
    Response object containing data received from the server

    Usage:
    Send a POST request to '/api/chat' endpoint with necessary data to be processed.

    Example:
    import requests

    url = 'http://localhost:5000/api/chat'
    data = {'query': 'What is the weather today?'}
    response = requests.post(url, json=data)

    """
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }
    json_data = request.json
    playback = json_data.get("playback")  # type: ignore
    record = json_data.get("record")  # type: ignore
    if record:
        del json_data["record"]  # type: ignore
    data = json.dumps(json_data)

    def generate():
        answer = ""
        raw_lines = ""
        if not playback:
            with requests.post(
                url, headers=headers, data=data, stream=True
            ) as response:
                response.raise_for_status()  # ensure we notice bad responses
                for line in response.iter_lines():
                    line_str = line.decode("utf-8")
                    raw_lines += line_str + "\n"
                    if line_str:
                        yield line_str + "\n"
                        rdata = line.lstrip(b"data: ").decode("utf-8")
                        if rdata == "[DONE]":
                            break
                        if not rdata:
                            continue
                        rdata = json.loads(rdata)
                        delta = rdata["choices"][0]["delta"]
                        if "content" not in delta:
                            continue
                        answer += delta["content"]

            code_blocks = []
            lines = answer.split("\n")
            in_code_block = False

            for line in lines:
                if "```" in line:  # This line is a delimiter
                    in_code_block = not in_code_block  # Change the state
                elif in_code_block:  # We're inside a code block
                    code_blocks.append(line.strip())

            # Print the resulting lines

            # with open("code_blocks.txt", "w") as f:
            #    f.write(str(code_blocks))
            if record:
                with open(os.path.join(test_dir, f"{record}.txt"), "w") as f:
                    f.write(str(raw_lines))
        else:
            with open(os.path.join(test_dir, f"{playback}.txt"), "r") as f:
                lines = f.readlines()
                for line in lines:
                    sleep(0.1)
                    yield line + "\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(port=5000)
