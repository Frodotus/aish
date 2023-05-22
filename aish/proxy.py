import json
import os
from time import sleep

import requests
from flask import Flask, Response, request

app = Flask(__name__)


@app.route("/api/chat", methods=["POST"])
def proxy():
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}",
    }
    data = json.dumps(request.json)
    playback = request.json.get("playback")  # type: ignore

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

            with open("output.txt", "w") as f:
                f.write(str(code_blocks))
            with open("output_raw.txt", "w") as f:
                f.write(str(raw_lines))
        else:
            with open("output_raw.txt", "r") as f:
                lines = f.readlines()
                for line in lines:
                    sleep(0.1)
                    yield line + "\n"

    return Response(generate(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(port=5000)
