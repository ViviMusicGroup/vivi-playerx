import re
import sys
import json
import urllib.request

IFRAME_API_URL = "https://www.youtube.com/iframe_api"
PLAYER_JS_URL_TEMPLATE = "https://www.youtube.com/s/player/{}/player_ias.vflset/en_GB/base.js"
CONFIG_FILE = "player_configs.json"

def get_current_player_hash():
    print("Fetching iframe_api to get current player hash...")
    try:
        req = urllib.request.Request(IFRAME_API_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
        match = re.search(r'\\?/s\\?/player\\?/([a-zA-Z0-9_-]+)\\?/', html)
        if match:
            return match.group(1)
    except Exception as e:
        print(f"Error fetching player hash: {e}")
    return None

def extract_cipher_config(player_hash):
    js_url = PLAYER_JS_URL_TEMPLATE.format(player_hash)
    print(f"Downloading player JS from {js_url}...")
    try:
        req = urllib.request.Request(js_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            js = response.read().decode('utf-8')
    except Exception as e:
        print(f"Error downloading player JS: {e}")
        return None

    # 1. Extract signature timestamp (sts)
    sts = None
    sts_match = re.search(r'signatureTimestamp\s*:\s*(\d+)|sts\s*:\s*(\d+)|"signatureTimestamp"\s*:\s*(\d+)', js)
    if sts_match:
        sts_str = next(g for g in sts_match.groups() if g is not None)
        sts = int(sts_str)

    # 2. Extract signature deobfuscation function and arguments
    sig = None

    # Modern 2026 nested caller pattern (e.g., zf(5,4574,Yz(17,6020,K.s)))
    nested_caller_match = re.search(
        r'([a-zA-Z0-9$_]+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*([a-zA-Z0-9$_]+)\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*[a-zA-Z0-9$_]+\.s\s*\)\s*\)',
        js
    )
    if nested_caller_match:
        groups = nested_caller_match.groups()
        sig = f"{groups[0]}({groups[1]},{groups[2]},{groups[3]}({groups[4]},{groups[5]},INPUT))"

    # Modern pattern: function name definition containing decodeURIComponent, followed by two-argument call
    if not sig:
        sig_def_match = re.search(
            r'([a-zA-Z0-9$_]+)=function\([a-zA-Z0-9$_]+,[a-zA-Z0-9$_]+,[a-zA-Z0-9$_]+\)\{var\s+[a-zA-Z0-9$_]+=[a-zA-Z0-9$_]+\^[a-zA-Z0-9$_]+;[^{}]+decodeURIComponent',
            js
        )
        if sig_def_match:
            sig_func_name = sig_def_match.group(1)
            sig_call_match = re.search(
                rf'\b{re.escape(sig_func_name)}\s*\(\s*(\d+)\s*,\s*(\d+)\s*,',
                js
            )
            if sig_call_match:
                sig = f"{sig_func_name}({sig_call_match.group(1)},{sig_call_match.group(2)},INPUT)"

    # Fallback to legacy signature extraction patterns
    if not sig:
        sig_match = re.search(r'([a-zA-Z0-9$_]{1,8})\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*decodeURIComponent\s*\(', js)
        if sig_match:
            func_name = sig_match.group(1)
            arg1 = sig_match.group(2)
            arg2 = sig_match.group(3)
            sig = f"{func_name}({arg1},{arg2},INPUT)"
        else:
            sig_match_fallback = re.search(r'([a-zA-Z0-9$_]{1,8})\s*\(\s*(\d+)\s*,\s*decodeURIComponent\s*\(', js)
            if sig_match_fallback:
                func_name = sig_match_fallback.group(1)
                arg = sig_match_fallback.group(2)
                sig = f"{func_name}({arg},INPUT)"

    # 3. Extract n-parameter transform class (nClass)
    n_class = None
    # Modern pattern: class instantiated inside get("n") flow
    n_class_match = re.search(
        r'new\s+g\.([a-zA-Z0-9$_]+)\s*\(\s*[a-zA-Z0-9$_]+\s*,\s*(?:!0|true)\s*\)\s*\)\s*\.\s*get\s*\(\s*["\']n["\']\s*\)',
        js
    )
    if n_class_match:
        n_class = n_class_match.group(1)
    else:
        # Fallback to legacy W_ / Ga / etc. patterns
        n_match = re.search(r'new\s+g\.([a-zA-Z0-9$_]+)\s*\(\s*["\']https://x\.googlevideo\.com/videoplayback\?n=["\']', js)
        if n_match:
            n_class = n_match.group(1)

    print(f"Extracted info: sts={sts}, sig={sig}, nClass={n_class}")
    
    if sts and sig and n_class:
        return {
            "sig": sig,
            "nClass": n_class,
            "sts": sts
        }
    return None

def main():
    player_hash = get_current_player_hash()
    if not player_hash:
        print("Failed to get current player hash.")
        sys.exit(1)

    print(f"Current player hash is: {player_hash}")

    # Read existing config file
    try:
        with open(CONFIG_FILE, "r") as f:
            config_data = json.load(f)
    except FileNotFoundError:
        # Initialize default config if not found
        config_data = {
            "schemaVersion": 1,
            "players": {}
        }
    except Exception as e:
        print(f"Error reading config file: {e}")
        sys.exit(1)

    players = config_data.get("players", {})

    # Check if hash is already present in configs or any aliases
    is_known = False
    for p_hash, p_data in players.items():
        if p_hash == player_hash or player_hash in p_data.get("aliases", []):
            is_known = True
            break

    if is_known:
        print(f"Player {player_hash} is already known. No update needed.")
        sys.exit(0)

    # Perform extraction
    extracted = extract_cipher_config(player_hash)
    if not extracted:
        print(f"Failed to extract deobfuscation config for player {player_hash}.")
        sys.exit(1)

    # Add to players mapping
    players[player_hash] = {
        "sig": extracted["sig"],
        "nClass": extracted["nClass"],
        "sts": extracted["sts"],
        "aliases": []
    }
    config_data["players"] = players

    # Save config file back
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=2)
        print(f"Successfully added player {player_hash} to {CONFIG_FILE}!")
    except Exception as e:
        print(f"Error writing config file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
