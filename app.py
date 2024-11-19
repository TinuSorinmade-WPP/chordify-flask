from flask import Flask, render_template, request
import pandas as pd
from tinuspotify import *  # Assuming all necessary functions like setup_spotify_credentials, etc., are imported

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    user_input = '1,4,1'  # Default chord progression
    num_pages = 1  # Default number of pages
    instrument = None  # Optional: instrument choice
    songs_df = pd.DataFrame()  # Initialize as empty DataFrame
    spotify_playlist_id = None  # For Spotify playlist ID
    youtube_playlist_id = None  # For YouTube playlist ID

    # Setup credentials
    auth_token = setup_hooktheory_credentials()
    sp = setup_spotify_credentials()

    if request.method == 'POST':
        try:
            # Get form inputs
            user_input = request.form.get('Chord', '')  # Chord progression entered by user
            num_pages = int(request.form.get('Page', 1))  # Number of pages to fetch
            instrument = request.form.get('instrument', '')  # Instrument preference
            
            if num_pages < 1:
                raise ValueError("Number of pages must be at least 1.")

            # Fetch songs from Hooktheory
            songs_df = get_tracks(user_input, num_pages, auth_token)

            # If instrument is provided and songs were found, add it to the songs dataframe
            if instrument and not songs_df.empty:
                songs_df['Instrument'] = instrument.title()

            # Create a Spotify playlist if songs are found
            if not songs_df.empty:
                playlist_name = f"{user_input} chord progression songs"
                spotify_playlist_id = create_spotify_playlist(sp, songs_df, playlist_name)
                print(f"Generated Spotify playlist ID: {spotify_playlist_id}")  # Debug output

                # Create a YouTube playlist and add tutorials
                youtube_playlist_title = f"{user_input} chord progression songs - {instrument} tutorials"
                youtube_playlist_description = f"A collection of tutorials for songs with a {user_input} chord progression."
                youtube = setup_youtube_credentials()  # Ensure YouTube credentials are set up
                youtube_playlist_id = create_youtube_playlist(youtube, youtube_playlist_title, youtube_playlist_description)
                
                if youtube_playlist_id:
                    # Correct function name to add tutorial videos to YouTube playlist
                    add_videos_to_youtube_playlist(youtube, youtube_playlist_id, songs_df, instrument)
                    print(f"Generated YouTube playlist ID: {youtube_playlist_id}")
                else:
                    print("YouTube playlist creation failed.")
            else:
                print("No songs found for the given chord progression.")

        except ValueError as e:
            print(f"Error in input: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    # Pass all variables to the template
    return render_template(
        'index.html',
        songs=songs_df,
        input=user_input,
        page=num_pages,
        instrument=instrument,
        playlist_id=spotify_playlist_id,
        youtube_playlist_id=youtube_playlist_id
    )
