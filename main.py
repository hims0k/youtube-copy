import os
import sys

import httplib2
from googleapiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


def get_credentials(
        scope,
        secret_file,
):
    missing_client_secret_message = """
    WARNING: Please configure OAuth 2.0

    To make this sample run you will need to populate the client_secrets.json file
    found at:

       %s

    with information from the API Console
    https://console.developers.google.com/

    For more information about the client_secrets.json file format, please visit:
    https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
    """ % os.path.abspath(
        os.path.join(os.path.dirname(__file__), secret_file)
    )

    flow = flow_from_clientsecrets(
        secret_file,
        message=missing_client_secret_message,
        scope=scope
    )

    storage = Storage("%s-oauth2.json" % sys.argv[0])
    cred = storage.get()

    if cred is None or cred.invalid:
        flags = argparser.parse_args()
        cred = run_flow(flow, storage, flags)

    return cred


def build_youtube_api(
        scope,
        client_secret_file
):
    credentials = get_credentials(scope, client_secret_file)

    youtube_api_service_name = "youtube"
    youtube_api_version = "v3"

    youtube_api = build(
        youtube_api_service_name,
        youtube_api_version,
        http=credentials.authorize(httplib2.Http())
    )

    return youtube_api


def insert_new_playlist(
        youtube_api,
        title,
        description,
        thumbnails=None,
        is_private=True
):
    if thumbnails is None:
        thumbnails = {}
    playlists_insert_response = youtube_api.playlists().insert(
        part="snippet,status",
        body=dict(
            snippet=dict(
                title=title,
                description=description,
                thumbnails=thumbnails if thumbnails is not None else {}
            ),
            status=dict(
                privacyStatus="private" if is_private else "public"
            )
        )
    ).execute()

    return playlists_insert_response["id"]


def get_playlist_information(
        youtube_api,
        playlist_id
):
    youtube_playlist_response = youtube_api.playlists().list(
        part="snippet,status",
        id=playlist_id
    ).execute()

    playlist = youtube_playlist_response["items"][0]

    return playlist["snippet"]


def copy_playlist(
        youtube_api,
        source_playlist_id,
        is_asc_order=True
):
    source_playlist = get_playlist_information(youtube, source_playlist_id)
    new_playlist_id = insert_new_playlist(
        youtube_api,
        source_playlist["title"],
        source_playlist["description"],
        source_playlist["thumbnails"],
    )

    video_ids = get_playlist_video_id(youtube, source_playlist_id, is_asc_order)
    insert_items_in_playlist(youtube, new_playlist_id, video_ids)

    return new_playlist_id


def get_playlist_video_id(
        youtube_api,
        playlist_id,
        is_asc_order=True
):
    resource_video_id = []

    # playlist items request
    playlist_item_list_request = youtube_api.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=100
    )

    # loop request till load all items in playlist
    while playlist_item_list_request:
        playlist_item_list_response = playlist_item_list_request.execute()

        # print playlist items
        for playlist_item in playlist_item_list_response["items"]:
            snippet = playlist_item["snippet"]
            resource_video_id.append(snippet["resourceId"]["videoId"])

        playlist_item_list_request = youtube_api.playlistItems().list_next(
            playlist_item_list_request,
            playlist_item_list_response
        )

    if not is_asc_order:
        resource_video_id.reverse()

    return resource_video_id


def insert_items_in_playlist(
        youtube_api,
        playlist_id,
        video_ids=None
):
    if video_ids is None:
        video_ids = []

    for video_id in video_ids:
        resource_id = dict(
            kind="youtube#video",
            videoId=video_id
        )

        response = youtube_api.playlistItems().insert(
            part="snippet",
            body=dict(
                snippet=dict(
                    playlistId=playlist_id,
                    resourceId=resource_id
                )
            )
        ).execute()

        print(response)


if __name__ == '__main__':
    YOUTUBE_READ_WRITE_SCOPE = 'https://www.googleapis.com/auth/youtube'
    CLIENT_SECRETS_FILE = "client_secret.json"

    PLAYLIST_ID = "XXX"

    youtube = build_youtube_api(YOUTUBE_READ_WRITE_SCOPE, CLIENT_SECRETS_FILE)

    copy_playlist(youtube, PLAYLIST_ID, False)
