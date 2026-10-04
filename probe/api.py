import json, requests, os
H={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36","Referer":"https://canlanstats.sportninja.com/"}
B="https://canlan2-api.sportninja.net/v1"
T="Nz7BgbzbxfrhWtft"; S="d6ieKFuhvhmS8Q7y"
os.makedirs("probe/out2",exist_ok=True)
def get(path,tag):
    try:
        r=requests.get(B+path,headers=H,timeout=20)
        body=r.text
    except Exception as e:
        return {"path":path,"err":str(e)}
    open(f"probe/out2/{tag}.json","w").write(body[:20000])
    return {"path":path,"status":r.status_code,"len":len(body),"head":body[:250]}
res=[]
g=requests.get(f"{B}/schedules/{S}/games",headers=H,timeout=20).json()
games=g.get("data",g)
res.append({"games_keys":list(g.keys()) if isinstance(g,dict) else None,"n":len(games) if isinstance(games,list) else None})
opp=None
if isinstance(games,list) and games:
    gm=games[0]; res.append({"game0_keys":list(gm.keys())})
    for side in ("homeTeam","visitingTeam"):
        t=gm.get(side) or {}
        if t.get("id")!=T: opp=t.get("id")
gid=games[0]["id"]
d=requests.get(f"{B}/games/{gid}",headers=H,timeout=20).json()["data"]
res.append({"game_keys":list(d.keys())})
p=d["playerRosters"][0]["players"][0]
res.append({"player_keys":list(p.keys())})
open("probe/out2/game.json","w").write(json.dumps(d)[:40000])
res.append({"opp":opp})
cands=[f"/teams/{T}",f"/teams/{T}/statistics",f"/teams/{T}/stats",f"/teams/{T}/players",f"/teams/{T}/roster",
 f"/teams/{T}/statistics?schedule_id={S}",f"/teams/{T}/statistics?sn_schedule={S}",
 f"/schedules/{S}",f"/schedules/{S}/standings",f"/schedules/{S}/statistics",f"/schedules/{S}/stats",
 f"/schedules/{S}/players/statistics",f"/schedules/{S}/teams",f"/schedules/{S}/teams/{T}/statistics",
 f"/schedules/{S}/leaders",f"/schedules/{S}/player-statistics",
 f"/stats/team?team_id={T}&schedule_id={S}",f"/statistics/team?team_id={T}&schedule_id={S}",
 f"/teams/{T}/players/statistics?schedule_id={S}",f"/teams/{T}/schedules/{S}/statistics",
 f"/teams/{T}/schedules/{S}/players",f"/schedules/{S}/games?team_id={T}"]
for i,c in enumerate(cands): res.append(get(c,f"c{i}"))
json.dump(res,open("probe/out2/summary.json","w"),indent=1)
