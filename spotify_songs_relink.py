# ==============================================================================
# Spotify Song Relinker & Auditor
#
# A comprehensive tool to audit and clean a Spotify library, supporting
# both "Liked Songs" and specific user-owned playlists via an interactive menu.
#
# Version: 2.1.0 (Final)
# ==============================================================================

# --- Import Required Libraries ---
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
import sys
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, Alignment
import argparse


# ==============================================================================
# --- IMPORTANT: USER CONFIGURATION ---
#
# You MUST fill in your Spotify API credentials below.
# These are obtained from the Spotify Developer Dashboard:
# https://developer.spotify.com/dashboard/
#
# ==============================================================================
CLIENT_ID = "YOUR_CLIENT_ID"
CLIENT_SECRET = "YOUR_CLIENT_SECRET"
REDIRECT_URI = "http://127.0.0.1:8888/callback" # use this url as callback uir for the app you create in your Spotify Developer Dashboard


def str_to_bool(value):
    """
    A helper function to convert command-line string arguments to booleans
    in a case-insensitive and user-friendly way.
    """
    if isinstance(value, bool):
        return value
    if value.lower() in ('true', 't', '1', 'yes', 'y'):
        return True
    elif value.lower() in ('false', 'f', '0', 'no', 'n'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected (e.g., True, false, t, 1, 0).')

def auto_fit_columns(worksheet):
    """
    A helper function to auto-fit the column widths for a given worksheet.
    """
    for col in worksheet.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length:
                    max_length = len(str(cell.value))
            except:
                pass
        adjusted_width = (max_length + 2)
        worksheet.column_dimensions[column].width = adjusted_width


def main():
    """
    Main function that orchestrates the entire audit and cleanup process.
    It is wrapped in a try...except block to handle user interruptions gracefully.
    """
    try:
        # --- Step 1: Set up and Parse Command-Line Arguments ---
        epilog_text = """
IMPORTANT:
Before running, you must fill in your CLIENT_ID and CLIENT_SECRET
variables at the top of the script file.

Usage Examples:
  Audit Liked Songs (Dry Run):
    python3 spotify_song_relink.py --dry-run True --market BE

  Audit using an interactive selection menu:
    python3 spotify_song_relink.py --dry-run True --market BE --select-from-list

  Audit a specific Playlist directly by ID (Dry Run):
    python3 spotify_song_relink.py --dry-run True --market BE --playlist-id 37i9dQZF1DXcBWIGoYBM5M
"""
        parser = argparse.ArgumentParser(
            description="A tool to audit and clean your Spotify Liked Songs or a specific playlist.",
            epilog=epilog_text,
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument('--dry-run', required=True, type=str_to_bool, help="Mandatory. 'True' or 'False' (case-insensitive).")
        parser.add_argument('--market', type=str, required=True, help="Mandatory. The 2-letter ISO country code for your market (e.g., US, BE, GB).")
        parser.add_argument('--playlist-id', type=str, default=None, help="Optional. The ID of a playlist to process. Ignored if --select-from-list is used.")
        parser.add_argument('--select-from-list', action='store_true', help="Optional. Show an interactive list of your Liked Songs and owned playlists to choose from.")
        parser.add_argument('--artist', type=str, default=None, help="Optional. Run in test mode for a specific artist. Enclose in quotes.")

        if len(sys.argv) == 1:
            parser.print_help(sys.stderr)
            sys.exit(1)

        args = parser.parse_args()
        DRY_RUN = args.dry_run
        USER_MARKET = args.market.upper()
        PLAYLIST_ID = args.playlist_id
        TEST_MODE_ARTIST = args.artist

        if TEST_MODE_ARTIST is not None and not TEST_MODE_ARTIST.strip():
            print("Error: --artist parameter cannot be an empty string.")
            sys.exit(1)

        # --- Step 2: Authenticate and Validate Inputs ---
        # Added playlist-read-private to the scope to be able to list user's playlists
        scope = "user-library-read user-library-modify playlist-read-private playlist-modify-public playlist-modify-private"
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, scope=scope))
        user = sp.current_user()
        print(f"Authenticated as {user['display_name']} ({user['id']})")
        
        available_markets = sp.available_markets()['markets']
        if USER_MARKET not in available_markets:
            print(f"\nError: '{args.market}' is not a valid Spotify market code.")
            sys.exit(1)
            
        # --- Step 3: Determine and Confirm the Song Source ---
        source_name = ""
        
        if args.select_from_list:
            print("\nFetching your playlists...")
            selection_options = [{'name': 'Liked Songs', 'id': 'liked_songs'}] # 'liked_songs' is a special internal ID
            
            offset = 0
            while True:
                playlists_page = sp.current_user_playlists(limit=50, offset=offset)
                if not playlists_page['items']:
                    break
                for playlist in playlists_page['items']:
                    # Only include playlists owned by the user
                    if playlist['owner']['id'] == user['id']:
                        selection_options.append({'name': playlist['name'], 'id': playlist['id']})
                offset += len(playlists_page['items'])
            
            print("\nPlease choose a source to process:")
            for i, option in enumerate(selection_options, 1):
                print(f"  {i}. {option['name']}")
                
            while True:
                try:
                    choice_str = input("\nEnter the number of your choice: ")
                    choice_index = int(choice_str)
                    if 1 <= choice_index <= len(selection_options):
                        selected_source = selection_options[choice_index - 1]
                        source_name = selected_source['name']
                        if selected_source['id'] == 'liked_songs':
                            PLAYLIST_ID = None
                        else:
                            PLAYLIST_ID = selected_source['id']
                        
                        confirm_source = input(f"You have selected '{source_name}'. Proceed? (y/n): ")
                        if confirm_source.lower() != 'y':
                            print("Aborting.")
                            sys.exit(0)
                        break
                    else:
                        print(f"Invalid number. Please enter a number between 1 and {len(selection_options)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
        
        elif PLAYLIST_ID:
            try:
                playlist = sp.playlist(PLAYLIST_ID)
                if playlist['owner']['id'] != user['id']:
                    print(f"\nError: You are not the owner of the playlist '{playlist['name']}'.")
                    sys.exit(1)
                source_name = f"Playlist '{playlist['name']}'"
            except spotipy.exceptions.SpotifyException:
                print(f"\nError: Playlist with ID '{PLAYLIST_ID}' not found or you do not have access.")
                sys.exit(1)
        else:
            source_name = "Liked Songs"

        # --- Step 4: Announce the Script's Operating Mode ---
        print(f"\nAuditing Source: {source_name}")
        print(f"Using market: '{USER_MARKET}'")
        
        if DRY_RUN:
            print("Mode: DRY RUN (no changes will be made)")
        else:
            print("Mode: LIVE RUN (changes WILL be made)")
            if TEST_MODE_ARTIST:
                print(f"--- ARTIST TEST MODE IS ACTIVE. ONLY MODIFYING TRACKS BY '{TEST_MODE_ARTIST}'. ---")
            confirm = input("Are you sure you want to continue? (y/n): ")
            if confirm.lower() != 'y':
                print("Aborting.")
                return

        # --- Step 5: The Main Audit Logic ---
        tracks_to_audit_log = []
        print(f"\nFetching songs from {source_name}...")
        offset = 0
        while True:
            # Conditional fetching based on mode
            if PLAYLIST_ID:
                results = sp.playlist_items(PLAYLIST_ID, limit=100, offset=offset, market=USER_MARKET)
            else:
                results = sp.current_user_saved_tracks(limit=50, offset=offset)

            if not results['items']: break
            
            original_track_map = {item['track']['id']: item['track'] for item in results['items'] if item and item.get('track') and item['track'].get('id')}
            track_ids = list(original_track_map.keys())

            if not track_ids:
                offset += len(results['items'])
                continue

            full_tracks_details = sp.tracks(track_ids, market=USER_MARKET)

            for resolved_track in full_tracks_details['tracks']:
                if not resolved_track: continue
                is_relinked = 'linked_from' in resolved_track and resolved_track['linked_from']
                is_unplayable = not resolved_track['is_playable']
                id_in_library = resolved_track['linked_from']['id'] if is_relinked else resolved_track['id']
                original_track = original_track_map.get(id_in_library)
                if not original_track: continue
                log_entry = {'artist': original_track['artists'][0]['name'], 'title': original_track['name'], 'old_album': original_track['album']['name'], 'old_id': id_in_library, 'new_album': '', 'new_id': '', 'reason': ''}
                if is_relinked:
                    log_entry['reason'] = 'Re-linked'
                    log_entry['new_id'] = resolved_track['id']
                    log_entry['new_album'] = resolved_track['album']['name']
                    print(f"\n[FOUND RE-LINKED TRACK]: '{log_entry['title']}' (by '{log_entry['artist']}')")
                elif is_unplayable:
                    log_entry['reason'] = 'Unplayable'
                    print(f"\n[FOUND UNPLAYABLE TRACK]: '{log_entry['title']}' (by '{log_entry['artist']}')")
                    query = f"{log_entry['title']} artist:{log_entry['artist']}"
                    search_results = sp.search(q=query, type='track', limit=5)
                    for potential_track in search_results['tracks']['items']:
                        if potential_track['is_playable'] and potential_track['name'].lower() == log_entry['title'].lower():
                            log_entry['new_id'] = potential_track['id']
                            log_entry['new_album'] = potential_track['album']['name']
                            print(f"  > Found replacement for unplayable track.")
                            break
                    if not log_entry['new_id']: print("  > No replacement found.")
                else:
                    log_entry['reason'] = 'OK'
                tracks_to_audit_log.append(log_entry)
            
            offset += len(results['items'])
            print(f"Processed {offset} songs...")

        # --- Step 6: Display Summary and Generate Enhanced Excel Report ---
        unplayable_count = len([t for t in tracks_to_audit_log if t['reason'] == 'Unplayable'])
        relinked_count = len([t for t in tracks_to_audit_log if t['reason'] == 'Re-linked'])
        clean_count = len([t for t in tracks_to_audit_log if t['reason'] == 'OK'])
        replacements_found = len([t for t in tracks_to_audit_log if t['new_id']])
        print("\n" + "="*40 + f"\n           Scan Complete - {source_name}\n" + "="*40)
        print(f"Total Tracks Audited: {len(tracks_to_audit_log)}")
        print(f"  - Clean:      {clean_count}")
        print(f"  - Unplayable: {unplayable_count}")
        print(f"  - Re-linked:  {relinked_count}")
        print(f"Total Replacements Found: {replacements_found}")
        print("="*40)
        if tracks_to_audit_log:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M")
            filename = f"spotify_song_audit_{timestamp}.xlsx"
            wb = openpyxl.Workbook()
            ws_summary = wb.active
            ws_summary.title = "Run Summary"
            ws_summary.append(["Run Parameters"])
            ws_summary['A1'].font = Font(bold=True, size=14)
            run_info = [("Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),("Authenticated User", user['display_name']),("Source Audited", source_name),("Run Mode", 'Dry Run (No Changes Made)' if DRY_RUN else 'Live Run (Changes Made)'),("Market", USER_MARKET),("Test Mode Artist", TEST_MODE_ARTIST if TEST_MODE_ARTIST else "N/A (Full Run)")]
            for row in run_info: ws_summary.append(row)
            ws_summary.append([]) 
            ws_summary.append(["Scan Statistics"])
            ws_summary[f'A{len(run_info) + 3}'].font = Font(bold=True, size=14)
            scan_stats = [("Category", "Count"),("Total Tracks Audited", len(tracks_to_audit_log)),("Clean Tracks", clean_count),("Unplayable Tracks", unplayable_count),("Re-linked Tracks", relinked_count),("Replacements Found", replacements_found)]
            for row in scan_stats: ws_summary.append(row)
            ws_summary['A10'].font = Font(bold=True)
            ws_summary['B10'].font = Font(bold=True)
            ws_summary['B10'].alignment = Alignment(horizontal='right')
            for i in range(11, 16): ws_summary[f'B{i}'].alignment = Alignment(horizontal='right')
            auto_fit_columns(ws_summary)
            ws_audit = wb.create_sheet("Audit Report")
            headers = ['Reason', 'Artist', 'Title', 'Old Album Name', 'Old Track Id', 'New Album Name', 'New Track Id']
            ws_audit.append(headers)
            for cell in ws_audit[1]: cell.font = Font(bold=True)
            for track in tracks_to_audit_log: ws_audit.append([track['reason'], track['artist'], track['title'], track['old_album'], track['old_id'], track['new_album'], track['new_id']])
            auto_fit_columns(ws_audit)
            wb.save(filename)
            print(f"\n[LOG CREATED]: A complete multi-sheet audit has been saved to '{filename}'")

        # --- Step 7: Perform Live Run Actions ---
        if not DRY_RUN:
            tracks_to_process = [t for t in tracks_to_audit_log if t['new_id']]
            if not tracks_to_process:
                print("\nNo tracks with found replacements to process.")
            else:
                print("\nStarting replacement process...")
                total_to_process = len(tracks_to_process)
                processed_count = 0
                for i, pair in enumerate(tracks_to_process, 1):
                    if TEST_MODE_ARTIST and pair['artist'].lower() != TEST_MODE_ARTIST.lower(): continue
                    progress_counter = f"({i} of {total_to_process})"
                    try:
                        if PLAYLIST_ID:
                            sp.playlist_add_items(PLAYLIST_ID, [pair['new_id']])
                            print(f"  {progress_counter} + Added new version: '{pair['title']}'")
                            sp.playlist_remove_all_occurrences_of_items(PLAYLIST_ID, [pair['old_id']])
                            print(f"  {' ' * len(progress_counter)} - Removed old version: '{pair['title']}'")
                        else: # Liked Songs mode
                            sp.current_user_saved_tracks_add(tracks=[pair['new_id']])
                            print(f"  {progress_counter} + Liked new version: '{pair['title']}'")
                            sp.current_user_saved_tracks_delete(tracks=[pair['old_id']])
                            print(f"  {' ' * len(progress_counter)} - Unliked old version: '{pair['title']}'")
                        processed_count += 1
                    except Exception as e:
                        print(f"An error occurred while replacing track {pair['old_id']}: {e}")
                print("\nCleanup complete!")
                if TEST_MODE_ARTIST:
                    print(f"Processed {processed_count} track(s) for artist '{TEST_MODE_ARTIST}'.")
        else:
            print("\nDry run complete. No changes were made.")
            if replacements_found > 0:
                print("To apply fixes for the found replacements, use --dry-run False.")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user - script did not complete all of its work!")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()