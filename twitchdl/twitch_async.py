"""
Twitch API access, but async.
"""

import time
from typing import Any, Mapping, Optional

import httpx

from twitchdl import CLIENT_ID
from twitchdl.entities import ClipAccessToken, Data
from twitchdl.twitch import Content, get_auth_token_from_context, gql_raise_on_error, log_request, log_response, raise_for_status


async def authenticated_post(
    client: httpx.AsyncClient,
    url: str,
    *,
    json: Any = None,
    content: Optional[Content] = None,
):
    headers = {"Client-ID": CLIENT_ID}

    auth_token = get_auth_token_from_context()
    if auth_token is not None:
        headers["authorization"] = f"OAuth {auth_token}"

    response = await request(client, "POST", url, content=content, json=json, headers=headers)
    raise_for_status(response, auth_token)
    return response


async def request(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    json: Any = None,
    content: Optional[Content] = None,
    headers: Optional[Mapping[str, str]] = None,
):
    request = client.build_request(method, url, json=json, content=content, headers=headers)
    log_request(request)
    start = time.time()
    response = await client.send(request)
    duration = time.time() - start
    log_response(response, duration)
    return response


async def gql_persisted_query(client: httpx.AsyncClient, query: Data):
    url = "https://gql.twitch.tv/gql"
    response = await authenticated_post(client, url, json=query)
    gql_raise_on_error(response)
    return response.json()


async def get_clip_access_token(client: httpx.AsyncClient, slug: str) -> ClipAccessToken:
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

    response = await gql_persisted_query(client, query)
    return response["data"]["clip"]
