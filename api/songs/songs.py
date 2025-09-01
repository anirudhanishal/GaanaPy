import asyncio
from fastapi import FastAPI, Query
from typing import Dict
from urllib.parse import urlparse

app = FastAPI()


class Songs:
    def __init__(self, aiohttp, api_endpoints, functions, errors):
        self.aiohttp = aiohttp
        self.api_endpoints = api_endpoints
        self.functions = functions
        self.errors = errors

    async def search_songs(self, search_query: str, limit: int) -> dict:
        response = await self.aiohttp.post(self.api_endpoints.search_songs_url + search_query)
        result = await response.json()
        track_ids = []
        for i in range(0, int(limit)):
            try:
                track_ids.append(result['gr'][0]['gd'][int(i)]['seo'])
            except (IndexError, TypeError, KeyError):
                pass

        if len(track_ids) == 0:
            return await self.errors.no_results()

        return await self.get_track_info(track_ids)

    async def get_track_info(self, track_id: list) -> dict:
        track_info = []
        for i in track_id:
            response = await self.aiohttp.post(self.api_endpoints.song_details_url + i)
            result = await response.json()
            track_info.extend(await asyncio.gather(
                *[self.format_json_songs(i) for i in result['tracks']]
            ))

        return {
            "success": True,
            "data": track_info
        }

    async def format_json_songs(self, results: dict) -> dict:
        data = {}
        try:
            data['seokey'] = results['seokey']
        except KeyError:
            return await self.errors.invalid_seokey()

        data['album_seokey'] = results['albumseokey']
        data['track_id'] = results['track_id']
        data['title'] = results['track_title']
        data['artists'] = await self.functions.findArtistNames(results['artist'])
        data['artist_seokeys'] = await self.functions.findArtistSeoKeys(results['artist'])
        data['artist_ids'] = await self.functions.findArtistIds(results['artist'])
        data['artist_image'] = results['artist_detail'][0]['atw']
        data['album'] = results['album_title']
        data['album_id'] = results['album_id']
        data['duration'] = results['duration']
        data['popularity'] = results['popularity']
        data['genres'] = await self.functions.findGenres(results['gener'])
        data['is_explicit'] = await self.functions.isExplicit(results['parental_warning'])
        data['language'] = results['language']
        data['label'] = results['vendor_name']
        data['release_date'] = results['release_date']
        data['play_count'] = results['play_ct']
        data['favorite_count'] = results['total_favourite_count']
        data['song_url'] = f"https://gaana.com/song/{data['seokey']}"
        data['album_url'] = f"https://gaana.com/album/{data['album_seokey']}"
        data['images'] = {
            'urls': {
                'large_artwork': results['artwork_large'],
                'medium_artwork': results['artwork_web'],
                'small_artwork': results['artwork']
            }
        }
        data['stream_urls'] = {'urls': {}}

        try:
            base_url = await self.functions.decryptLink(results['urls']['medium']['message'])
            data['stream_urls']['urls']['very_high_quality'] = base_url.replace("64.mp4", "320.mp4")
            data['stream_urls']['urls']['high_quality'] = base_url.replace("64.mp4", "128.mp4")
            data['stream_urls']['urls']['medium_quality'] = base_url
            data['stream_urls']['urls']['low_quality'] = base_url.replace("64.mp4", "16.mp4")
        except KeyError:
            data['stream_urls']['urls']['very_high_quality'] = ""
            data['stream_urls']['urls']['high_quality'] = ""
            data['stream_urls']['urls']['medium_quality'] = ""
            data['stream_urls']['urls']['low_quality'] = ""

        return data


# ------------------- FastAPI Endpoint -------------------
@app.get("/songs/info/", response_model=Dict)
async def song_info(seokey: str = Query(..., description="Full Gaana song URL")):
    """
    Accepts a full Gaana song URL and returns song info JSON.
    Example:
    /songs/info/?seokey=https://gaana.com/song/deha-ru-chhadini
    """
    if seokey.startswith("http"):
        parsed_url = urlparse(seokey)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[0] == "song":
            seokey_extracted = path_parts[1]
        else:
            return {"success": False, "error": "Invalid Gaana song URL"}
    else:
        return {"success": False, "error": "Please provide a full Gaana song URL"}

    # Initialize your dependencies here (aiohttp session, endpoints, functions, errors)
    from some_module import aiohttp, api_endpoints, functions, errors  # <- replace with actual imports

    songs = Songs(aiohttp, api_endpoints, functions, errors)
    return await songs.get_track_info([seokey_extracted])
