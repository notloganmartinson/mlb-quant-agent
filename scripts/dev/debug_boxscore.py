import statsapi
import json

game_pk = 718522
try:
    box = statsapi.boxscore_data(game_pk)
    # The 'homePitchers' and 'awayPitchers' lists in boxscore_data often contain summary/header rows.
    # Let's look at the 'home' -> 'players' dictionary which is more reliable.
    home_players = box.get('home', {}).get('players', {})
    
    print("Searching for a pitcher in 'home' -> 'players'...")
    for pid, data in home_players.items():
        stats = data.get('stats', {}).get('pitching', {})
        if stats:
            print(f"Player: {data.get('person', {}).get('fullName')} (ID: {pid})")
            print(f"Pitching Stats Keys: {stats.keys()}")
            print(f"Strikeouts ('strikeOuts'): {stats.get('strikeOuts')}")
            break

    # Also check why hp[0] failed - it was a header row
    hp = box.get('homePitchers', [])
    if len(hp) > 1:
        print(f"\nSecond item in homePitchers: {hp[1].get('name')} | K: {hp[1].get('k')}")

except Exception as e:
    import traceback
    traceback.print_exc()
