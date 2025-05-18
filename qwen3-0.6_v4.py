import warnings
warnings.filterwarnings(action='ignore')

import requests
import sys
import json

# --- Configuration ---
LLAMA_CPP_SERVER_URL = "http://127.0.0.1:8080"
MODEL_NAME = "Qwen3-0.6B" 
NCTX = 12000  # Example context length, adjust as needed for your model/setup
COUNTERLIMITS = 16 # Reset history after this many turns
# Define stop sequences relevant to your model to prevent run-on responses
STOPS = ['<|im_end|>']

def applyTemplate(server_url: str, message: list):
    """
    Sends text to the llama.cpp /apply-template endpoint.Args:
        server_url: The base URL of the llama.cpp server (e.g., "http://127.0.0.1:8080").
        messages: ChatML formatted list.
    Returns:
        A string with applied tokens.
    """
    endpoint = "/apply-template"
    full_url = server_url.rstrip('/') + endpoint # Ensure no double slash
    payload = {
        "messages": message
    }
    headers = {
        "Content-Type": "application/json"
    }
    try:
        # Send the POST request
        response = requests.post(full_url, headers=headers, json=payload)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        # Parse the JSON response
        res1 = response.json()
        return res1['prompt']
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to or communicating with the server at {full_url}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server responded with status {e.response.status_code}: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from the server.")
        print("Response text:", response.text)
        return None

def tokenize_text(server_url: str, text: str, add_special: bool = False, with_pieces: bool = False):
    """
    Sends text to the llama.cpp /tokenize endpoint.
    Args:
        server_url: The base URL of the llama.cpp server (e.g., "http://127.0.0.1:8080").
        text: The string content to tokenize.
    Returns:
        An integer with the token count, or None if an error occurred.
    """
    endpoint = "/tokenize"
    full_url = server_url.rstrip('/') + endpoint # Ensure no double slash
    # Prepare the data payload as a Python dictionary
    payload = {
        "content": text,
    }
    # Set the headers (requests usually does this automatically with json=...)
    headers = {
        "Content-Type": "application/json"
    }
    try:
        # Send the POST request
        response = requests.post(full_url, headers=headers, json=payload)
        # Raise an exception for bad status codes (4xx or 5xx)
        response.raise_for_status()
        # Parse the JSON response
        res1 = response.json()
        return len(res1['tokens'])
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to or communicating with the server at {full_url}: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Server responded with status {e.response.status_code}: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print("Error: Could not decode JSON response from the server.")
        print("Response text:", response.text)
        return None

def bot(messages):
    import requests
    import json
    BASE_URL = "http://localhost:8080/v1"
    MODEL_NAME = "Qwen3-0.6B" 
    STOPS = ['<|im_end|>']
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.3,
        "frequency_penalty": 1.6,
        "max_tokens": 1600, # Adjust as needed
        "stream": True,
        "stop": STOPS
        # Add other parameters your Llama.cpp server supports, e.g.:
        # "n_predict": 1000, # llama.cpp specific equivalent to max_tokens
        # "top_k": 40,
        # "top_p": 0.9,
        # "repeat_penalty": 1.1
    }
    #message in case of error
    servererror = {"role": "assistant", "content": "Your AI is not responding..."}
    try:
        response = session.post(
            f"{BASE_URL}/chat/completions",
            json=payload,
            stream=True  # Crucial for streaming
        )
        response.raise_for_status()  # Raise an HTTPError for bad responses (4XX or 5XX)

        assistant_response_content = ""
        
        for line_bytes in response.iter_lines():
            if line_bytes:
                decoded_line = line_bytes.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_data_str = decoded_line[len("data: "):].strip()
                    if json_data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(json_data_str)
                        if chunk.get("choices") and len(chunk["choices"]) > 0:
                            delta = chunk["choices"][0].get("delta", {})
                            content_piece = delta.get("content")
                            if content_piece:
                                print(content_piece, end="", flush=True)
                                assistant_response_content += content_piece
                    except json.JSONDecodeError:
                        # This might happen if the server sends a non-JSON line or an incomplete JSON
                        # print(f"\n[SYSTEM DEBUG] Non-JSON or malformed data line: {json_data_str}", file=sys.stderr)
                        pass # Ignoring malformed lines for now, can be logged
        
        print() # Add a newline after the assistant's full response is printed

        if assistant_response_content: # Only add to history if content was received
            history = {"role": "assistant", "content": assistant_response_content}
        return history
    except requests.exceptions.ConnectionError as e:
        print(f"\033[0;31m\n[ERROR] Could not connect to Llama.cpp server at {BASE_URL}.")
        print(f"Details: {e}\033[0m")
        print("Please ensure the server is running and accessible.")
        return servererror
    except requests.exceptions.HTTPError as e:
        print(f"\033[0;31m\n[ERROR] HTTP error occurred: {e.response.status_code} {e.response.reason}")
        print(f"Response: {e.response.text}\033[0m")
        # Depending on the error, you might want to break or allow retry
        return servererror
    except requests.exceptions.RequestException as e:
        print(f"\033[0;31m\n[ERROR] An unexpected error occurred with the request: {e}\033[0m")
        return servererror
    except Exception as e: # Catch any other unexpected errors
        print(f"\033[0;31m\n[CRITICAL ERROR] An unexpected error occurred: {e}\033[0m")
        import traceback
        traceback.print_exc()
        return servererror
       

# --- Initialization ---
print(f"✅ Ready to Chat with {MODEL_NAME} (llama.cpp server)")
print(f"   Context length (NCTX): {NCTX} tokens")
print(f"   History will be reset after {COUNTERLIMITS} interactions.")
print(f"   Stop sequences: {STOPS}")
print("\033[0m")  # Reset all colors
history = []
print("\033[92;1m")  # Green color for assistant's initial prompt (if any) or first response
counter = True
# Create a session for persistent connections and default headers
session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    # If your Llama.cpp server is configured to require an API key (even a dummy one):
    # "Authorization": "Bearer not-needed"
})

# --- Main Chat Loop ---
while True:
    userinput = ""
    print("\033[1;30m")  # Dark grey for user prompt instructions
    print("\n\nEnter your message (Ctrl+D on Unix/macOS or Ctrl+Z+Enter on Windows to submit multi-line input).")
    print("Type 'quit!' on a new line and submit to exit.")
    print("\033[91;1mYou: ")  # Red for user input prompt
    
    lines = []
    try:
        while True:
            line = sys.stdin.readline()
            if not line:  # EOF (Ctrl+D or Ctrl+Z+Enter)
                break
            if line.strip().lower() == "quit!":
                lines.append(line) # Ensure "quit!" is processed
                break
            lines.append(line)
        userinput = "".join(lines).strip()

    except KeyboardInterrupt:  # Handle Ctrl+C
        print("\033[0m\nBYE BYE! (Interrupted)")
        break
    
    if not userinput: # If only EOF was sent without text
        print("\033[0;33m[SYSTEM] No input received. Try again or type 'quit!' to exit.\033[92;1m")
        continue

    if userinput.lower() == "quit!": # Check the fully formed input
        print("\033[0mBYE BYE!")
        break

    history.append({"role": "user", "content": userinput})
    # Check context window availability against chat_history
    formattedPrompt = applyTemplate(LLAMA_CPP_SERVER_URL,history)
    usedTokens = tokenize_text(LLAMA_CPP_SERVER_URL, formattedPrompt)
    if (NCTX - usedTokens) < 1600: # less than max tokens from the LLM call
        print("\033[0;33m")  # Yellow for system message
        print(f"\n[SYSTEM] Context window overflow almost reached. Resetting chat history.")
        history = []
        history.append({"role": "user", "content": userinput})
        counter = 1  # Reset counter
        print("\033[92;1m")  # Back to green for assistant
    print("\033[1;30m")  # Dark grey for user prompt instructions
    print(f"\nUsed Context window: {usedTokens}")

    
    print("\033[92;1mAssistant: ") # Green for assistant output
    reply = bot(history)
    formattedPrompt = applyTemplate(LLAMA_CPP_SERVER_URL,[reply])
    usedTokens = tokenize_text(LLAMA_CPP_SERVER_URL, formattedPrompt)
    print("\033[1;30m")  # Dark grey for user prompt instructions
    print(f"\nGenerated tokens: {usedTokens}")   
    history.append(reply)  
    formattedPrompt = applyTemplate(LLAMA_CPP_SERVER_URL,history)
    usedTokens = tokenize_text(LLAMA_CPP_SERVER_URL, formattedPrompt)    
    print(f"Used Context window: {usedTokens}")    
    



print("\033[0m") # Reset all colors at the end

"""
Key Changes and Explanations:

Imports:

requests: For making HTTP requests.
json: For parsing the JSON data in the stream.
sys: For stdin.
Configuration (BASE_URL, MODEL_NAME, NCTX, etc.):

MODEL_NAME is crucial. You must change "your-local-model-name" to the actual model identifier that your Llama.cpp server is configured to use for the /v1/chat/completions endpoint. This might be the model file name (e.g., llama-2-7b-chat.Q4_K_M.gguf) or an alias if you've set one up in the server command.
STOPS: Added a more comprehensive list of common stop tokens. Adjust these based on how your specific model was trained or how it behaves.
requests.Session():

A requests.Session() object is used to persist certain parameters across requests, like headers. It can also reuse underlying TCP connections, which can be more efficient.
Content-Type: application/json is set as a default header.
An optional Authorization header is commented out; uncomment and use if your Llama.cpp server requires it (even a dummy key like "not-needed").
Input Loop (sys.stdin.readline()):

The input reading loop now reads line by line until an EOF is encountered (Ctrl+D on Unix/macOS, Ctrl+Z then Enter on Windows). This allows for multi-line input.
userinput.strip().lower() == "quit!" checks for the quit command.
KeyboardInterrupt (Ctrl+C) is handled for a graceful exit.
API Request Payload:

The payload dictionary is constructed to match the OpenAI API /v1/chat/completions endpoint.
"stream": True is included to tell the server to send a streaming response.
"stop": STOPS provides the stop sequences to the LLM.
Commented out are other common Llama.cpp parameters (n_predict, top_k, etc.) you might want to add if your server supports them via the OpenAI-compatible endpoint.
Making the Request (session.post):

session.post(f"{BASE_URL}/chat/completions", json=payload, stream=True):
json=payload: requests automatically converts the Python dictionary to a JSON string for the request body.
stream=True: This is critical. It tells requests not to download the entire response at once. Instead, the connection remains open, and you can iterate over the incoming data.
Processing the Streaming Response (response.iter_lines()):

response.raise_for_status(): Will raise an exception if the server returns an HTTP error code (like 4xx or 5xx).
response.iter_lines(): Iterates over the response data line by line as it arrives from the server. Each line_bytes is a bytes object.
decoded_line = line_bytes.decode('utf-8'): Decodes the bytes to a UTF-8 string.
Server-Sent Events (SSE) Format: The Llama.cpp server (and other OpenAI-compatible servers) use the SSE format for streaming. Each piece of data is typically prefixed with data:.
if decoded_line.startswith("data: "):: Checks for this prefix.
json_data_str = decoded_line[len("data: "):].strip(): Extracts the actual JSON string.
if json_data_str == "[DONE]": break: The stream is terminated by a special message data: [DONE].
chunk = json.loads(json_data_str): Parses the JSON string.
The subsequent logic extracts delta.content similar to your original code, prints it immediately (flush=True), and appends it to assistant_response_content.
Error Handling:

Includes try...except blocks for requests.exceptions.ConnectionError (if the server is down), requests.exceptions.HTTPError (for server-side errors), and general requests.exceptions.RequestException.
A general Exception catch is included for unexpected issues, printing a traceback.
History Management:

The assistant's complete response (assistant_response_content) is appended to the history list after the stream is finished, only if content was actually received.
Before Running:

Install requests:
Bash

pip install requests
CRITICAL: Update MODEL_NAME: Change "your-local-model-name" to the correct identifier for your model as configured in your Llama.cpp server. If you start llama.cpp like server -m models/my_model.gguf -c 2048, then MODEL_NAME would likely be models/my_model.gguf or whatever the server reports as the available model. Check your Llama.cpp server startup logs or its documentation for how it expects the model to be specified in API calls. Sometimes it's just the filename.
Ensure Llama.cpp Server is Running: Make sure your Llama.cpp server is started and accessible at http://localhost:8080 (or update BASE_URL if it's different). It needs to be started with the --api-key flag if you intend to use an API key (even a dummy one) and the -m <model_path> flag. For OpenAI compatibility, you typically start it in server mode. Example:
Bash

./server -m /path/to/your/model.gguf -c <NCTX_VALUE> --port 8080
Adjust NCTX in the script and -c in the server command to match.
This modified script should give you the desired streaming chat experience with your local Llama.cpp instance using the requests library.
"""

