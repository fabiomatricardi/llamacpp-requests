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
    # Parsing multi-lines
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
    # handling exceptions
    except KeyboardInterrupt:  # Handle Ctrl+C
        print("\033[0m\nBYE BYE! (Interrupted)")
        break    
    if not userinput: # If only EOF was sent without text
        print("\033[0;33m[SYSTEM] No input received. Try again or type 'quit!' to exit.\033[92;1m")
        continue
    if userinput.lower() == "quit!": # Check the fully formed input
        print("\033[0mBYE BYE!")
        break
    # CHAT START
    history.append({"role": "user", "content": userinput})
    # Check context window availability against chat_history
    formattedPrompt = applyTemplate(LLAMA_CPP_SERVER_URL,history)
    usedTokens = tokenize_text(LLAMA_CPP_SERVER_URL, formattedPrompt)
    # If context overflow RESET the chat history
    if (NCTX - usedTokens) < 1600: # less than max tokens from the LLM call
        print("\033[0;33m")  # Yellow for system message
        print(f"\n[SYSTEM] Context window overflow almost reached. Resetting chat history.")
        history = []
        history.append({"role": "user", "content": userinput})
        counter = 1  # Reset counter
        print("\033[92;1m")  # Back to green for assistant
    print("\033[1;30m")  # Dark grey for user prompt instructions
    print(f"\nUsed Context window: {usedTokens}")
    # CHAT assistant reply
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


