import sqlite3
from pathlib import Path
from datetime import date

db = Path(r'C:\Users\AUDIOVST\Desktop\Projects\nba rook trajectory\data\processed\nba_season.db')
readme = Path(r'C:\Users\AUDIOVST\Desktop\Projects\nba rook trajectory\README.md')

conn = sqlite3.connect(str(db))
cur = conn.cursor()
cur.execute('''
    SELECT player_name, team_abbr, COUNT(DISTINCT game_id) as gp,
           SUM(points) as pts, SUM(assists) as ast, SUM(rebounds) as reb, SUM(plus_minus) as pm
    FROM season_player_stats
    WHERE is_rookie=1 AND season_type IN ('regular','playoffs')
    GROUP BY player_id
''')
rows = cur.fetchall()
conn.close()

data = []
for r in rows:
    name, team, gp, pts, ast, reb, pm = r
    if gp >= 3:
        data.append({'name':name,'team':team,'ppg':pts/gp,'apg':ast/gp,'rpg':reb/gp,'pmg':pm/gp})
data.sort(key=lambda x:(x['pmg'],x['ppg']), reverse=True)
data = data[:10]

lines = []
lines.append(f'_Updated {date.today()} · ranked by +/- per game · min 3 games_')
lines.append('')
lines.append('| # | Player | Team | PPG | APG | RPG | +/- |')
lines.append('|---|--------|------|-----|-----|-----|-----|')
for i,d in enumerate(data,1):
    lines.append(f'| {i} | {d["name"]} | {d["team"]} | {d["ppg"]:.1f} | {d["apg"]:.1f} | {d["rpg"]:.1f} | {d["pmg"]:+.1f} |')

section = '<!-- TOP_PERFORMERS:START -->\n' + '\n'.join(lines) + '\n<!-- TOP_PERFORMERS:END -->'
text = readme.read_text(encoding='utf-8')
before = text.split('<!-- TOP_PERFORMERS:START -->')[0]
after = text.split('<!-- TOP_PERFORMERS:END -->')[1]
readme.write_text(before + section + after, encoding='utf-8')
print('done')
