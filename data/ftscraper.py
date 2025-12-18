import asyncio
import json
import os
import time

import aiohttp

_knownLeagues = [
    # 2025
    'tcayla26m7uvbd9j',  # Carl Yastrzemski League
    'efr7mfsfm7uulh5z',  # Champs League
    'm2ctep1hm7w3sy8w',  # Dick Allen League
    's1tg5fnum7uvbihw',  # Dwight Gooden League
    'voz4vq2hm7uvb50p',  # Frank Robinson League
    '3duby9wdm7uvbg6l',  # Fred Lynn League
    'eqgdfimrm7uvba9m',  # Jimmie Foxx League
    '942toa9tm7uyab7j',  # Joe Medwick League
    '7ehvwpnpm7uull8u',  # Mickey Mantle League
    'b83d7gnsm7uvb7vl',  # Roger Hornsby League
    'jif60ch2m7ql120g',  # Mock Draft 1
    # 2024
    'vbq66tzwlt90u0wn',  # Champs League
    'lau29fdlltglxf9o',  # Dave Stieb League
    'licuwv9rltgljhic',  # Dock Ellis League
    'bch2s58mltglvgag',  # Gary Carter League
    'wjr4x6cwltgm29pk',  # Hank Aaron League
    'lr1l35tjltglswc2',  # Honus Wagner League
    'fc6aucqkltglmsze',  # Pee Wee Reese League
    'dni9kexbltgm0myz',  # Stan Musial League
    'l44bp72nltglg4mf',  # Ted Williams League
    '2ozvvpnzltglr1ht',  # Ty Cobb League
    'i706amybltjp2k78',  # Willie Mays League
    'lt863x0xlt912y2j',  # Mock Draft A
    'gdbkakpolt90wqci',  # Mock Draft B
    # 2023
    'jjdx7yonlf7kocfz',  # Champs League
    'zmktszyulf7lg617',  # Eckersley League
    'ijsu1v16lf7mfhll',  # Koufax League
    '8fghinaalf7lryh5',  # Maddux League
    '5wxxh74wlf7m57gg',  # Martinez League
    'mzdd4ysmlf7lydv1',  # Ryan League
    # 2022
    '8yqaz060l0ofblha',  # Champs League
    'ixvd2dlil0r8ray1',  # Clemens League
    'vhioum1ll0r8rpqw',  # Gibson League
    'jxoa9dq9l0r8rgli',  # McCovey League
    '8k8at6ill0q94oyc',  # Ortiz League
    # 2021
    'y8q1j409kmeel9cp',  # Bonds League
    'h0nia07fkmedpvk2',  # Griffey League
    '6qy7dqwakmici8im',  # Ichiro League
    'i8a6jclykmefo93i',  # Pujols League
]
ft_session = None
request_sem = asyncio.Semaphore(5)  # Limit concurrent requests to 5


def _is_cache_file_too_old(filepath: str, max_age_seconds: int = 86400) -> bool:
    """Utility function for checking if a cache file is too old (default is >1 day)."""

    if not os.path.exists(filepath):
        return True
    file_mod_time = os.path.getmtime(filepath)
    current_time = time.time()
    return (current_time - file_mod_time) > max_age_seconds


async def _fantrax_api_request(url: str, method: str, headers: dict = {}, params: dict = {}) -> dict:
    """Utility function for querying the Fantrax API with a rate-limiter attached to avoid spamming requests."""

    global ft_session
    ft_session = aiohttp.ClientSession('https://www.fantrax.com')

    if not headers:
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }

    async with ft_session as api:
        retry_count = 0
        max_retries = 3

        async with request_sem:
            while retry_count < max_retries:
                try:
                    print(f'Sending request - ({method.upper()} to {url})')
                    resp = await api.request(
                        method.upper(), url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)
                    )
                    json_resp = await resp.json(content_type=resp.content_type)
                    # Fantrax sometimes returns errors with response code 200...
                    if 'error' in json_resp:
                        raise Exception(f'Fantrax API error: {json_resp["error"]}')
                    return json_resp
                except asyncio.TimeoutError:
                    # Retry requests that time out... Fantrax can be very finicky and slow, so we don't want to assume our first requests work.
                    retry_count += 1
                except Exception as e:
                    raise Exception(f'Fantrax API request failed: {e}')
            # If we reach here, all retries have failed.
            raise Exception(f'Fantrax API request ({method.upper()} for {url}) timed out after multiple retries.')


async def request_player_data() -> dict:
    if not _is_cache_file_too_old('data/.cache/player_data.json'):
        with open('data/.cache/player_data.json', 'r') as f:
            try:
                player_data = json.load(f)
                print('Using cached player data.')
                return player_data
            except Exception:
                pass

    url = '/fxea/general/getPlayerIds?sport=MLB'
    try:
        player_data = await _fantrax_api_request(url, 'GET')
        with open('data/.cache/player_data.json', 'w') as f:
            json.dump(player_data, f, indent=2)
        return player_data
    except Exception as e:
        print(f'Error fetching player data: {e}')
        return {}


async def request_league_info(league_ids: list[str]) -> dict:
    league_info_results = {}

    info_requests = {}
    for league_id in league_ids:
        if not _is_cache_file_too_old(f'data/.cache/league_info_{league_id}.json'):
            with open(f'data/.cache/league_info_{league_id}.json', 'r') as f:
                try:
                    league_info_results[league_id] = json.load(f)
                    print(f'Using cached league info for {league_id}.')
                except Exception:
                    pass
            continue

        url = f'/fxea/general/getLeagueInfo?leagueId={league_id}'
        info_requests[league_id] = _fantrax_api_request(url, 'GET')

    responses = await asyncio.gather(*info_requests.values(), return_exceptions=True)
    for league_id, resp in zip(league_ids, responses):
        with open(f'data/.cache/league_info_{league_id}.json', 'w') as f:
            json.dump(resp, f, indent=2)
        league_info_results[league_id] = resp

    return league_info_results


async def main():
    try:
        player_data = await request_player_data()
        if player_data:
            print(f'Fetched {len(player_data)} players.')
        else:
            print('Failed to fetch player data.')

        print(f'Fetching league info for {len(_knownLeagues)} leagues...')
        league_info = await request_league_info(_knownLeagues)
    except Exception as e:
        await ft_session.close()
        raise e


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Process interrupted by user.')
