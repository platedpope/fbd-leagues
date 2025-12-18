import json, os, time, requests, ratelimit

_knownLeagues = [
    # 2025 
    'tcayla26m7uvbd9j', # Carl Yastrzemski League
    'efr7mfsfm7uulh5z', # Champs League
    'm2ctep1hm7w3sy8w', # Dick Allen League
    's1tg5fnum7uvbihw', # Dwight Gooden League
    'voz4vq2hm7uvb50p', # Frank Robinson League
    '3duby9wdm7uvbg6l', # Fred Lynn League
    'eqgdfimrm7uvba9m', # Jimmie Foxx League
    '942toa9tm7uyab7j', # Joe Medwick League
    '7ehvwpnpm7uull8u', # Mickey Mantle League
    'b83d7gnsm7uvb7vl', # Roger Hornsby League
    'jif60ch2m7ql120g', # Mock Draft 1
    # 2024
    'vbq66tzwlt90u0wn', # Champs League
    'lau29fdlltglxf9o', # Dave Stieb League
    'licuwv9rltgljhic', # Dock Ellis League
    'bch2s58mltglvgag', # Gary Carter League
    'wjr4x6cwltgm29pk', # Hank Aaron League
    'lr1l35tjltglswc2', # Honus Wagner League
    'fc6aucqkltglmsze', # Pee Wee Reese League
    'dni9kexbltgm0myz', # Stan Musial League
    'l44bp72nltglg4mf', # Ted Williams League
    '2ozvvpnzltglr1ht', # Ty Cobb League
    'i706amybltjp2k78', # Willie Mays League
    'lt863x0xlt912y2j', # Mock Draft A
    'gdbkakpolt90wqci', # Mock Draft B
    # 2023
    'jjdx7yonlf7kocfz', # Champs League
    'zmktszyulf7lg617', # Eckersley League
    'ijsu1v16lf7mfhll', # Koufax League
    '8fghinaalf7lryh5', # Maddux League
    '5wxxh74wlf7m57gg', # Martinez League
    'mzdd4ysmlf7lydv1', # Ryan League
    # 2022
    '8yqaz060l0ofblha', # Champs League
    'ixvd2dlil0r8ray1', # Clemens League
    'vhioum1ll0r8rpqw', # Gibson League
    'jxoa9dq9l0r8rgli', # McCovey League
    '8k8at6ill0q94oyc', # Ortiz League
    # 2021
    'y8q1j409kmeel9cp', # Bonds League
    'h0nia07fkmedpvk2', # Griffey League
    '6qy7dqwakmici8im', # Ichiro League
    'i8a6jclykmefo93i', # Pujols League
]

def _is_cache_file_too_old(filepath: str, max_age_seconds: int = 86400) -> bool:
    """Utility function for checking if a cache file is too old (default is >1 day)."""

    if not os.path.exists(filepath):
        return True
    file_mod_time = os.path.getmtime(filepath)
    current_time = time.time()
    return (current_time - file_mod_time) > max_age_seconds

@ratelimit.sleep_and_retry
@ratelimit.limits(calls=3, period=1)
def _fantrax_api_request(url: str, method: str, headers: dict = None, params: dict = None):
    if params is None:
        params = {}
    if headers is None:
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }

    if method.upper() == 'POST':
        response = requests.post(url, headers=headers, json=params, timeout=10)
    elif method.upper() == 'GET':
        response = requests.get(url, headers=headers, params=params, timeout=10)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
    response.raise_for_status()
    
    jsonResponse = response.json()
    # Fantrax sometimes return errors with response code 200...
    if 'error' in jsonResponse:
        raise Exception(f"Fantrax API Error: {jsonResponse['error']}")
    return jsonResponse

def request_player_data():
    player_data = None

    if not _is_cache_file_too_old('data/.cache/player_data.json'):
        print('Using cached player data.')
        with open('data/.cache/player_data.json', 'r') as f:
            player_data = json.load(f)
    else:
        url = 'https://www.fantrax.com/fxea/general/getPlayerIds?sport=MLB'

        try:
            player_data = _fantrax_api_request(url, 'GET')
            with open('data/.cache/player_data.json', 'w') as f:
                json.dump(player_data, f, indent=2)
        except Exception as e:
            print(f"Error fetching player data: {e}")
            return None
    
    return player_data

if __name__ == '__main__':
    data = request_player_data()
    if data:
        print(f"Fetched {len(data)} players.")
    else:
        print("Failed to fetch player data.")