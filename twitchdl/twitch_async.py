"""
Twitch API implemented as async functions.
"""

import time
from typing import Any, AsyncGenerator, Dict, Mapping, Optional, Union

import httpx

from twitchdl import CLIENT_ID
from twitchdl.entities import (
    Clip,
    ClipAccessToken,
    ClipsPeriod,
    Data,
)
from twitchdl.exceptions import ConsoleError
from twitchdl.twitch import CLIP_FIELDS, gql_raise_on_error, log_request, log_response

Content = Union[str, bytes]
Headers = Dict[str, str]


async def authenticated_post(
    url: str,
    *,
    json: Any = None,
    content: Optional[Content] = None,
    auth_token: Optional[str] = None,
) -> httpx.Response:
    headers = {"Client-ID": CLIENT_ID}
    if auth_token is not None:
        headers["authorization"] = f"OAuth {auth_token}"

    response = await request("POST", url, content=content, json=json, headers=headers)
    if response.status_code == 400:
        data = response.json()
        raise ConsoleError(data["message"])

    response.raise_for_status()

    return response


async def request(
    method: str,
    url: str,
    json: Any = None,
    content: Optional[Content] = None,
    headers: Optional[Mapping[str, str]] = None,
):
    async with httpx.AsyncClient() as client:
        request = client.build_request(method, url, json=json, content=content, headers=headers)
        log_request(request)
        start = time.time()
        response = await client.send(request)
        duration = time.time() - start
        log_response(response, duration)
        return response


async def gql_persisted_query(query: Data):
    url = "https://gql.twitch.tv/gql"
    response = await authenticated_post(url, json=query)
    gql_raise_on_error(response)
    return response.json()


async def gql_query(query: str, auth_token: Optional[str] = None):
    url = "https://gql.twitch.tv/gql"
    response = await authenticated_post(url, json={"query": query}, auth_token=auth_token)
    gql_raise_on_error(response)
    return response.json()


async def channel_clips_generator(
    channel_id: str,
    period: ClipsPeriod,
    limit: int,
) -> AsyncGenerator[Clip, None]:
    async def _generator(clips: Data, limit: int) -> AsyncGenerator[Clip, None]:
        for clip in clips["edges"]:
            if limit < 1:
                return
            yield clip["node"]
            limit -= 1

        has_next = clips["pageInfo"]["hasNextPage"]
        if limit < 1 or not has_next:
            return

        req_limit = min(limit, 100)
        cursor = clips["edges"][-1]["cursor"]
        clips = await get_channel_clips(channel_id, period, req_limit, cursor)
        async for item in _generator(clips, limit):
            yield item

    req_limit = min(limit, 100)
    clips = await get_channel_clips(channel_id, period, req_limit)
    return _generator(clips, limit)


async def get_channel_clips(
    channel_id: str,
    period: ClipsPeriod,
    limit: int,
    after: Optional[str] = None,
):
    """
    List channel clips.

    At the time of writing this:
    * filtering by game name returns an error
    * sorting by anything but VIEWS_DESC or TRENDING returns an error
    * sorting by VIEWS_DESC and TRENDING returns the same results
    * there is no totalCount
    """
    query = f"""
    {{
      user(login: "{channel_id}") {{
        clips(
          first: {limit},
          after: "{after or ''}",
          criteria: {{
            period: {period.upper()},
            sort: VIEWS_DESC
          }}
        )
        {{
          pageInfo {{
            hasNextPage
            hasPreviousPage
          }}
          edges {{
            cursor
            node {{
              {CLIP_FIELDS}
            }}
          }}
        }}
      }}
    }}
    """

    response = await gql_query(query)
    user = response["data"]["user"]
    if not user:
        raise ConsoleError(f"Channel {channel_id} not found")

    return response["data"]["user"]["clips"]


async def get_clip_access_token(slug: str) -> ClipAccessToken:
    query = {
        "operationName": "VideoAccessToken_Clip",
        "variables": {"slug": slug},
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "36b89d2507fce29e5ca551df756d27c1cfe079e2609642b4390aa4c35796eb11",
            }
        },
    }

    response = await gql_persisted_query(query)
    return response["data"]["clip"]
