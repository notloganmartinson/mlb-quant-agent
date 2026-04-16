import statsapi
from scripts.generate_training_data import get_rolling_feature_map

season = 2023
feature_map, _, _ = get_rolling_feature_map(season)

# Pick a player, e.g., Mike Trout (545361)
# Find his first game date in 2023
data = statsapi.get('people', {'personIds': '545361', 'hydrate': 'stats(group=hitting,type=gameLog,season=2023)'})
first_game_date = data['people'][0]['stats'][0]['splits'][-1]['date'] # gameLog is usually desc, but let's be sure
dates = sorted([s['date'] for s in data['people'][0]['stats'][0]['splits']])
first_game = dates[0]

print(f"Mike Trout's first game in 2023: {first_game}")
val = feature_map.get((545361, first_game, 'h', 'R'))
print(f"Stats on first game vs RHP: {val}")

if abs(val['iso'] - 0.160) < 0.001 and abs(val['woba'] - 0.315) < 0.001:
    print("ROW-1 TEST PASSED")
else:
    print("ROW-1 TEST FAILED")
