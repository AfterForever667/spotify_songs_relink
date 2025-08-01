# Spotify Song Relinker

A command-line tool to audit and clean your Spotify library. It can operate on your main "Liked Songs" library or on a specific playlist you own, selectable via an interactive menu. The script identifies and fixes common issues like unplayable "grayed-out" tracks and outdated track links, and generates a complete Excel manifest of the selected song source.
The main reason why I created this script is that I'm using Home Assistant and Music Assistant quite intensively. I have very customized dashboard that show at a glance what is playing (from radio, from spotify, ...). 
When a song is playing on the radio, I'm getting some additional information for it from the internet. For example, the country the artist is from, the original release year of the song and the album cover-art. But I also check if the song that is playing is liked in my spotify library. Often I come across songs for which the spotify API returns "not liked" whereas I'm sure the song is in my library.
Investigation showed that when I lookup the song via the API it gives me a track-id that is different from the track-id in my liked songs (due to spotify's track re-linking mechanism). To solve that my library needs to be updated with the most recent track-id's for the songs in it. That is exactly what this tool does. 
By extension it can also check playlists, but the re-linking mechanism doesn't pose any problem in playlists. Here unplayable tracks are more of an issue (tracks that disappear from spotify). This tool tries to find whether a new track can be found that is likely the same as the one that disappeared (e.g. a track that disappeared may be on a compilation somewhere).
This script came to be with the help of IA (vibe coding).
**Although thoroughly tested, you are still using this at your own risk**


## What Problem Does This Solve?

Over time, your Spotify library and playlists can accumulate "stale" tracks due to changes in licensing, album re-releases, or regional availability. This script addresses two main problems:

1.  **Unplayable Tracks:** These are the "grayed-out" songs that you can no longer play. This tool finds them, searches for a playable version on Spotify, and replaces the old one if a suitable match is found.

2.  **Re-linked Tracks:** A more subtle issue where a track is still playable, but Spotify is silently redirecting you from an old track ID to a new one. This often happens when a song is moved to a compilation or a remastered album. While this doesn't affect playback, it means your library contains outdated references. This tool finds these outdated links and replaces them with the modern, canonical track ID.

The script requires a **market code** (your country's 2-letter code) to accurately check for track availability and linking in your region. The result is a cleaner, more up-to-date collection and a complete Excel backup for your records.

## Prerequisites

Before you begin, you will need:
- **Python 3:** [Download from python.org](https://www.python.org/downloads/)
- **Pip:** Python's package installer, which usually comes with Python.
- **A Spotify Account:** A free or premium account.
- **A Spotify Developer App:** This is free and necessary to get API credentials. You can create one on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/).

## Setup Instructions

1.  **Download the Script:**
    Save the `spotify_song_relink.py` script to a new folder on your computer.

2.  **Install Required Libraries:**
    Open your terminal or command prompt, navigate to the folder where you saved the script, and run the following command:
    ```bash
    pip3 install spotipy openpyxl
    ```

3.  **Get Spotify API Credentials:**
    - Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/) and log in.
    - Click "Create an App".
    - Give it a name (e.g., "My Song Relinker") and a description.
    - Once created, you will see your **Client ID**. Click "Show client secret" to see the **Client Secret**.
    - Click "Edit Settings". In the "Redirect URIs" box, add this exact URL: `http://127.0.0.1:8888/callback`.
    - Click "Save" at the bottom of the page.

4.  **Edit the Script:**
    Open the `spotify_song_relink.py` file in a text editor. Find the "USER CONFIGURATION" section at the top and replace the placeholder text with your actual **Client ID** and **Client Secret**.

    ```python
    # ...
    CLIENT_ID = "YOUR_CLIENT_ID_GOES_HERE"
    CLIENT_SECRET = "YOUR_CLIENT_SECRET_GOES_HERE"
    REDIRECT_URI = "http://127.0.0.1:8888/callback"
    # ...
    ```

## How to Run the Script

You run the script from your terminal. Both the `--dry-run` and `--market` parameters are mandatory.

**Note on parameters:** For convenience, the values for `--dry-run`, `--market`, and `--artist` are all **case-insensitive**.

**To see the help message:**
```bash
python3 spotify_song_relink.py --help
```
To Audit your Liked Songs (Dry Run):
This is the default mode if no playlist is specified. It scans and reports without making changes.

```bash
python3 spotify_song_relink.py --dry-run true --market be
```
To Audit using an Interactive Selection Menu (Recommended):
This is the most user-friendly way to choose what to audit. It will present a numbered list of your Liked Songs and all playlists you own.

```bash
python3 spotify_song_relink.py --dry-run true --market be --select-from-list
```
To Audit a specific Playlist directly by ID (Dry Run):
To get a playlist's ID, go to the playlist in Spotify, click the "..." menu, select "Share", and then "Copy Spotify URI". The ID is the long string after spotify:playlist:. The --select-from-list flag will override this if both are used.

```bash
python3 spotify_song_relink.py --dry-run true --market be --playlist-id 37i9dQZF1DXcBWIGoYBM5M
```
To perform a Live Run (Test Mode):
To test the script's modification capabilities safely, you can run it in live mode but limit it to a single artist. This example uses the interactive menu.

```bash
python3 spotify_song_relink.py --dry-run false --market be --select-from-list --artist "Artist Name"
```
## What to Expect
**Console Output:** The script will print its progress to the terminal, showing you which tracks it identifies as problematic and whether it finds replacements.
**Excel Report:** After the scan is complete, an Excel file named spotify_song_audit_yyyymmdd-hhmm.xlsx will be saved in the same folder. This file contains two sheets:
1. Run Summary: A high-level overview of how the script was run, including the user, source (Liked Songs or playlist name), mode, market, and a table with the final scan statistics.
2. Audit Report: A complete, detailed list of every song from the audited source, with a "Reason" column indicating if a track is "OK", "Unplayable", or "Re-linked", along with the old and new track/album details.
