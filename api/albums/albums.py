import asyncio
from urllib.parse import urlparse

class Albums:
    async def search_albums(self, search_query: str, limit: int) -> dict:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints
        errors = self.errors
        response = await aiohttp.post(endpoints.search_albums_url + search_query)
        result = await response.json()
        album_ids = []
        for i in range(0, int(limit)):
            try:
                album_ids.append(result['gr'][0]['gd'][int(i)]['seo'])
            except (IndexError, TypeError, KeyError):
                pass

        if len(album_ids) == 0:
            return await errors.no_results()

        return await self.get_album_info(album_ids, False)

    async def get_album_info(self, album_id: list, info: bool) -> dict:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints
        album_info = []
        if info is True:
            self.info = True

        def extract_seokey(input_str: str) -> str:
            if input_str.startswith("http"):
                parsed_url = urlparse(input_str)
                path_parts = parsed_url.path.strip("/").split("/")
                if len(path_parts) >= 2 and path_parts[0] == "album":
                    return path_parts[1]
                else:
                    raise ValueError("Invalid Gaana album URL")
            return input_str

        for i in album_id:
            try:
                seokey = extract_seokey(i)
            except ValueError:
                continue  # Skip invalid URLs

            response = await aiohttp.post(endpoints.album_details_url + seokey)
            result = await response.json()
            album_info.extend(await asyncio.gather(
                *[self.format_json_albums(result) for _ in range(0, 1)]
            ))

        return {
            "success": True,
            "data": album_info
        }

    async def get_album_tracks(self, album_id: str) -> list:
        aiohttp = self.aiohttp
        endpoints = self.api_endpoints

        def extract_seokey(input_str: str) -> str:
            if input_str.startswith("http"):
                parsed_url = urlparse(input_str)
                path_parts = parsed_url.path.strip("/").split("/")
                if len(path_parts) >= 2 and path_parts[0] == "album":
                    return path_parts[1]
                else:
                    raise ValueError("Invalid Gaana album URL")
            return input_str

        try:
            seokey = extract_seokey(album_id)
        except ValueError:
            return []

        response = await aiohttp.post(endpoints.album_details_url + seokey)
        result = await response.json()
        track_seokeys = [i['seokey'] for i in result['tracks']]
        result = await self.get_track_info(track_seokeys)
        return result

    async def format_json_albums(self, results: dict) -> dict:
        functions = self.functions
        errors = self.errors
        data = {}
        try:
            data['seokey'] = results['album']['seokey']
        except (IndexError, TypeError, KeyError):
            return await errors.no_results()

        data['album_id'] = results['album']['album_id']
        data['title'] = results['album']['title']
        try:
            data['artists'] = await functions.findArtistNames(results['album']['artist'])
            data['artist_seokeys'] = await functions.findArtistSeoKeys(results['tracks'][0]['artist'])
            data['artist_ids'] = await functions.findArtistIds(results['tracks'][0]['artist'])
        except (KeyError, IndexError):
            data['artists'] = ""
            data['artist_seokeys'] = ""
            data['artist_ids'] = ""

        data['duration'] = results['album']['duration']
        data['is_explicit'] = await functions.isExplicit(results['album']['parental_warning'])
        data['language'] = results['album']['language']
        data['label'] = results['album']['recordlevel']
        data['track_count'] = results['album']['trackcount']

        try:
            data['release_date'] = results['album']['release_date']
        except KeyError:
            data['release_date'] = ""

        data['play_count'] = results['album']['al_play_ct']
        data['favorite_count'] = results['album']['favorite_count']
        data['album_url'] = f"https://gaana.com/album/{results['album']['seokey']}"
        data['images'] = {
            'urls': {
                'large_artwork': results['album']['artwork'].replace("size_s.jpg", "size_l.jpg"),
                'medium_artwork': results['album']['artwork'].replace("size_s.jpg", "size_m.jpg"),
                'small_artwork': results['album']['artwork']
            }
        }

        if getattr(self, "info", False) is True:
            data['tracks'] = await self.get_album_tracks(data['seokey'])

        self.info = False
        return data
