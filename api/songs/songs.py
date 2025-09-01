# songs_api.py
import asyncio
from fastapi import FastAPI, Query
from typing import List, Dict
from urllib.parse import urlparse
import traceback

# ----------------- Songs Class -----------------
class Songs:
    def __init__(self, aiohttp=None, api_endpoints=None, functions=None, errors=None):
        self.aiohttp = aiohttp
        self.api_endpoints = api_endpoints
        self.functions = functions
        self.errors = errors

    async def search_songs(self, search_query: str, limit: int) -> dict:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints
        errors = self.errors
        response = await aiohttp.post(endpoints.search_songs_url + search_query)
        result = await response.json()
        track_ids = []
        for i in range(0, int(limit)):
            try:
                track_ids.append(result['gr'][0]['gd'][int(i)]['seo'])
            except (IndexError, TypeError, KeyError):
                pass

        if len(track_ids) == 0:
            return await errors.no_results()

        return await self.get_track_info(track_ids)

    async def get_track_info(self, track_id: list) -> dict:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints
        track_info = []
        for i in track_id:
            response = await aiohttp.post(endpoints.song_details_url + i)
            result = await response.json()
            track_info.extend(await asyncio.gather(
                *[self.format_json_songs(i) for i in result.get('tracks', [])]
            ))

        return {
            "success": True,
            "data": track_info
        }

    async def format_json_songs(self, results: dict) -> dict:
        functions = self.functions
        errors = self.errors
        data = {}
        try:
            data['seokey'] = results['seokey']
        except KeyError:
            return await errors.invalid_seokey()

        data['album_seokey'] = results.get('albumseokey', '')
        data['track_id'] = results.get('track_id', '')
        data['title'] = results.get('track_title', '')
        data['artists'] = await functions.findArtistNames(results.get('artist', []))
        data['artist_seokeys'] = await functions.findArtistSeoKeys(results.get('artist', []))
        data['artist_ids'] = await functions.findArtistIds(results.get('artist', []))
        data['artist_image'] = results.get('artist_detail', [{}])[0].get('atw', '')
        data['album'] = results.get('album_title', '')
        data['album_id'] = results.get('album_id', '')
        data['duration'] = results.get('duration', 0)
        data['popularity'] = results.get('popularity', 0)
        data['genres'] = await functions.findGenres(results.get('gener', []))
        data['is_explicit'] = await functions.isExplicit(results.get('parental_warning', False))
        data['language'] = results.get('language', '')
        data['label'] = results.get('vendor_name', '')
        data['release_date'] = results.get('release_date', '')
        data['play_count'] = results.get('play_ct', 0)
        data['favorite_count'] = results.get('total_favourite_count', 0)
        data['song_url'] = f"https://gaana.com/song/{data['seokey']}"
        data['album_url'] = f"https://gaana.com/album/{data['album_seokey']}"
        data['images'] = {
            'urls': {
                'large_artwork': results.get('artwork_large', ''),
                'medium_artwork': results.get('artwork_web', ''),
                'small_artwork': results.get('artwork', '')
            }
        }
        data['stream_urls'] = {'urls': {}}
        try:
            base_url = await functions.decryptLink(results['urls']['medium']['message'])
            data['stream_urls']['urls']['very_high_quality'] = base_url.replace("64.mp4", "320.mp4")
            data['stream_urls']['urls']['high_quality'] = base_url.replace("64.mp4", "128.mp4")
            data['stream_urls']['urls']['medium_quality'] = base_url
            data['stream_urls']['urls']['low_quality'] = base_url.replace("64.mp4", "16.mp4")
        except (KeyError, AttributeError):
            data['stream_urls']['urls']['very_high_quality'] = ""
            data['stream_urls']['urls']['high_quality'] = ""
            data['stream_urls']['urls']['medium_quality'] = ""
            data['stream_urls']['urls']['low_quality'] = ""

        return data

# ----------------- FastAPI App -----------------
app = FastAPI()

# ----------------- Songs instance -----------------
# Replace None with actual implementations
songs = Songs(aiohttp=None, api_endpoints=None, functions=None, errors=None)

# ----------------- Endpoint -----------------
@app.get("/songs/info/", response_model=Dict)
async def song_info(seokey: str = Query(..., description="Full Gaana song URL or just seokey")):
    """
    Returns song info JSON for a given Gaana song URL or seokey.
    Example:
    /songs/info/?seokey=https://gaana.com/song/deha-ru-chhadini
    """
    try:
        # Extract seokey if full URL
        if seokey.startswith("http"):
            path_parts = urlparse(seokey).path.strip("/").split("/")
            if len(path_parts) >= 2 and path_parts[0] == "song":
                seokey = path_parts[1]
            else:
                return {"success": False, "error": "Invalid Gaana song URL"}

        return await songs.get_track_info([seokey])

    except Exception as e:
        return {"success": False, "error": str(e), "trace": traceback.format_exc()}

