import os
import pickle
import requests
import json
import pandas as pd
from random import choice
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import spotipy.util as util
import spotipy

# Constants for YouTube API
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']

# Setup Spotify Credentials
def setup_spotify_credentials():
    credentials_file = "spotify-keys.json"
    with open(credentials_file, "r") as keys:
        api_tokens = json.load(keys)

    username = api_tokens["username"]
    client_id = api_tokens["client_id"]
    client_secret = api_tokens["client_secret"]
    redirect_uri = api_tokens["redirect"]

    scope = 'user-read-private user-read-playback-state user-modify-playback-state playlist-modify-public user-library-read'
    token = util.prompt_for_user_token(
        username, scope, client_id=client_id, client_secret=client_secret, redirect_uri=redirect_uri
    )

    return spotipy.Spotify(auth=token)

# Setup HookTheory Credentials
def setup_hooktheory_credentials():
    with open('Details.json', 'r') as file:
        credentials = json.load(file)

    response = requests.post("https://api.hooktheory.com/v1/users/auth", json=credentials)
    response.raise_for_status()
    return response.json().get("activkey")

# Fetch songs with a specific chord progression from HookTheory
def get_tracks(chord_progression, num_pages, auth_token):
    all_songs = []
    for page in range(1, num_pages + 1):
        headers = {"Accept": "application/json", "Authorization": f"Bearer {auth_token}"}
        url = f"https://api.hooktheory.com/v1/trends/songs?cp={chord_progression}&page={page}"
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            songs = response.json()
            if not songs:
                break
            all_songs.extend(songs)
        else:
            print(f"Error fetching data: {response.status_code} - {response.text}")
            break

    return pd.DataFrame([
        {'Artist': song['artist'].strip().title(), 'Song': song['song'].strip().title()}
        for song in all_songs
    ])

# Create a Spotify playlist
def create_spotify_playlist(sp, songs_df, playlist_name):
    songs = []

    for index, row in songs_df.iterrows():
        artist = row['Artist']
        title = row['Song']
        
        # Create the query string to search by artist and title
        query = f"artist:{artist} track:{title}"
        print(f"Querying Spotify with: {query}")

        try:
            # Search for the track in Spotify
            search_results = sp.search(q=f"artist: {artist} track: {title}", type="track", limit=1)


            # Debugging outputz
            print(f"Search results: {search_results}")

            # Check if any results were returned
            if search_results['tracks']['items']:
                first_song = search_results['tracks']['items'][0]
                songs.append(first_song['uri'])
            else:
                print(f"No match found for '{title}' by '{artist}'.")

        except Exception as e:
            print(f"Error searching for '{title}' by '{artist}': {e}")

    # Check if songs were found
    if not songs:
        print("No songs found. Playlist creation aborted.")
        return None

    # Create the playlist
    try:
        # Load Spotify API credentials from a JSON file
        credentials_file = "spotify-keys.json"
        with open(credentials_file, "r") as keys:
            api_tokens = json.load(keys)
        
        # Extract the username from the credentials
        username = api_tokens["username"]

        # Define playlist details
        playlist_name = "Songs with a chord progression"
        playlist_description = f"A playlist of {len(songs)} songs with the chord progression"

        # Create the playlist
        my_playlist = sp.user_playlist_create(
            user=username,
            name=playlist_name,
            public=True,
            description=playlist_description
        )
        
        # Add tracks to the playlist
        playlist_id = my_playlist['id']
        print(f"Playlist ID: {playlist_id}")

        results = sp.user_playlist_add_tracks(username, playlist_id, songs)
        
        print(f"Playlist '{playlist_name}' created successfully with ID: {playlist_id}")
        return playlist_id

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


# YouTube API Authentication
def setup_youtube_credentials():
    credentials = None

    # Check if token.pickle exists and is valid
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            credentials = pickle.load(token)

    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            # Only reload client_secret.json if no valid token exists
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', scopes=YOUTUBE_SCOPES)
            credentials = flow.run_local_server(port=8080)

        # Save the credentials to token.pickle for future use
        with open('token.pickle', 'wb') as token:
            pickle.dump(credentials, token)

    return build("youtube", "v3", credentials=credentials)

# Create a YouTube playlist
def create_youtube_playlist(youtube, title, description):
    request = youtube.playlists().insert(
        part="snippet,status",
        body={
            "snippet": {"title": title, "description": description},
            "status": {"privacyStatus": "public"}
        }
    )
    response = request.execute()
    return response["id"]

# Add videos to YouTube playlist
def add_videos_to_youtube_playlist(youtube, playlist_id, songs_df, instrument):
    for _, row in songs_df.iterrows():
        query = f"{row['Song']} by {row['Artist']} - {instrument} tutorial"
        search_request = youtube.search().list(q=query, part="snippet", type="video", maxResults=1)
        search_response = search_request.execute()
        if search_response["items"]:
            video_id = search_response["items"][0]["id"]["videoId"]
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": playlist_id,
                        "resourceId": {"kind": "youtube#video", "videoId": video_id}
                    }
                }
            ).execute()
        else:
            print(f"No results found for query: {query}")


# Main Function
if __name__ == "__main__":
    # Fetch songs from HookTheory
    chord_progression = "1-5-6-4"
    hook_auth = setup_hooktheory_credentials()
    songs_df = get_tracks(chord_progression, 3, hook_auth)

    if not songs_df.empty:
        # Spotify playlist creation
        sp = setup_spotify_credentials()
        spotify_playlist_name = f"Songs with {chord_progression} progression"
        spotify_playlist_id = create_spotify_playlist(sp, songs_df, spotify_playlist_name)

        if spotify_playlist_id:
            print(f"Spotify playlist '{spotify_playlist_name}' created successfully.")
            
            # YouTube playlist creation
            youtube = setup_youtube_credentials()
            youtube_playlist_name = f"{chord_progression} Tutorials"
            youtube_playlist_description = f"Tutorials for songs with {chord_progression} progression"
            
            # Pass both title and description
            youtube_playlist_id = create_youtube_playlist(youtube, youtube_playlist_name, youtube_playlist_description)

            if youtube_playlist_id:
                print(f"YouTube playlist '{youtube_playlist_name}' created successfully.")
                
                # Add videos to YouTube playlist
                add_videos_to_youtube_playlist(youtube, youtube_playlist_id, songs_df, "guitar")
            else:
                print("YouTube playlist creation failed.")
        else:
            print("Spotify playlist creation failed.")
