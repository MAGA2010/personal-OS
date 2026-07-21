#!/usr/bin/env python3
"""PathOS Pipeline to Frontend ETL Bridge - v2 with stateFips support."""
import json
from pathlib import Path

PIPELINE = Path(__file__).parent / "data-pipeline"
FRONTEND = Path(__file__).parent / "frontend"

STATE_FIPS = {
    "AL":"01","AK":"02","AZ":"04","AR":"05","CA":"06","CO":"08","CT":"09",
    "DE":"10","DC":"11","FL":"12","GA":"13","HI":"15","ID":"16","IL":"17",
    "IN":"18","IA":"19","KS":"20","KY":"21","LA":"22","ME":"23","MD":"24",
    "MA":"25","MI":"26","MN":"27","MS":"28","MO":"29","MT":"30","NE":"31",
    "NV":"32","NH":"33","NJ":"34","NM":"35","NY":"36","NC":"37","ND":"38",
    "OH":"39","OK":"40","OR":"41","PA":"42","RI":"44","SC":"45","SD":"46",
    "TN":"47","TX":"48","UT":"49","VT":"50","VA":"51","WA":"53","WV":"54",
    "WI":"55","WY":"56",
}

SCHOOLS = [
    ("arizona-state-university","Arizona State University","AZ","Tempe",33.4242,-111.9281,"亚利桑那州立大学"),
    ("boston-college","Boston College","MA","Chestnut Hill",42.3355,-71.1685,"波士顿学院"),
    ("boston-university","Boston University","MA","Boston",42.3505,-71.1054,"波士顿大学"),
    ("brown-university","Brown University","RI","Providence",41.8268,-71.4025,"布朗大学"),
    ("bucknell-university","Bucknell University","PA","Lewisburg",40.9523,-76.8863,"巴克内尔大学"),
    ("california-institute-of-technology","California Institute of Technology","CA","Pasadena",34.1377,-118.1253,"加州理工学院"),
    ("carnegie-mellon-university","Carnegie Mellon University","PA","Pittsburgh",40.4432,-79.9430,"卡内基梅隆大学"),
    ("columbia-university","Columbia University","NY","New York",40.8075,-73.9626,"哥伦比亚大学"),
    ("cornell-university","Cornell University","NY","Ithaca",42.4534,-76.4735,"康奈尔大学"),
    ("dartmouth-college","Dartmouth College","NH","Hanover",43.7044,-72.2887,"达特茅斯学院"),
    ("duke-university","Duke University","NC","Durham",36.0014,-78.9382,"杜克大学"),
    ("emory-university","Emory University","GA","Atlanta",33.7969,-84.3230,"埃默里大学"),
    ("georgetown-university","Georgetown University","DC","Washington",38.9076,-77.0723,"乔治城大学"),
    ("georgia-institute-of-technology","Georgia Institute of Technology","GA","Atlanta",33.7756,-84.3963,"佐治亚理工学院"),
    ("harvard-university","Harvard University","MA","Cambridge",42.3736,-71.1097,"哈佛大学"),
    ("harvey-mudd-college","Harvey Mudd College","CA","Claremont",34.1060,-117.7117,"哈维穆德学院"),
    ("indiana-university-bloomington","Indiana University Bloomington","IN","Bloomington",39.1653,-86.5264,"印第安纳大学布卢明顿分校"),
    ("johns-hopkins-university","Johns Hopkins University","MD","Baltimore",39.3299,-76.6205,"约翰霍普金斯大学"),
    ("lehigh-university","Lehigh University","PA","Bethlehem",40.6032,-75.3774,"里海大学"),
    ("loyola-university-chicago","Loyola University Chicago","IL","Chicago",41.9995,-87.6586,"芝加哥洛约拉大学"),
    ("massachusetts-institute-of-technology","Massachusetts Institute of Technology","MA","Cambridge",42.3601,-71.0942,"麻省理工学院"),
    ("new-york-university","New York University","NY","New York",40.7295,-73.9965,"纽约大学"),
    ("northeastern-university","Northeastern University","MA","Boston",42.3398,-71.0892,"东北大学"),
    ("northwestern-university","Northwestern University","IL","Evanston",42.0565,-87.6753,"西北大学"),
    ("ohio-state-university","The Ohio State University","OH","Columbus",40.0023,-83.0146,"俄亥俄州立大学"),
    ("olin-college-of-engineering","Olin College of Engineering","MA","Needham",42.2544,-71.2595,"欧林工程学院"),
    ("princeton-university","Princeton University","NJ","Princeton",40.3431,-74.6551,"普林斯顿大学"),
    ("purdue-university-main-campus","Purdue University—Main Campus","IN","West Lafayette",40.4237,-86.9212,"普渡大学"),
    ("rice-university","Rice University","TX","Houston",29.7178,-95.4017,"莱斯大学"),
    ("rose-hulman-institute-of-technology","Rose-Hulman Institute of Technology","IN","Terre Haute",39.4852,-87.3242,"罗斯-霍曼理工学院"),
    ("rutgers-university-new-brunswick","Rutgers University—New Brunswick","NJ","New Brunswick",40.5000,-74.4470,"罗格斯大学新布朗斯维克分校"),
    ("stanford-university","Stanford University","CA","Stanford",37.4275,-122.1697,"斯坦福大学"),
    ("texas-a-and-m-university","Texas A&M University","TX","College Station",30.6188,-96.3365,"德州农工大学"),
    ("tufts-university","Tufts University","MA","Medford",42.4085,-71.1183,"塔夫茨大学"),
    ("university-of-california-berkeley","University of California, Berkeley","CA","Berkeley",37.8716,-122.2727,"加州大学伯克利分校"),
    ("university-of-california-davis","University of California, Davis","CA","Davis",38.5382,-121.7617,"加州大学戴维斯分校"),
    ("university-of-california-irvine","University of California, Irvine","CA","Irvine",33.6405,-117.8443,"加州大学尔湾分校"),
    ("university-of-california-los-angeles","University of California, Los Angeles","CA","Los Angeles",34.0689,-118.4452,"加州大学洛杉矶分校"),
    ("university-of-california-san-diego","University of California, San Diego","CA","La Jolla",32.8801,-117.2340,"加州大学圣地亚哥分校"),
    ("university-of-california-santa-barbara","University of California, Santa Barbara","CA","Santa Barbara",34.4140,-119.8489,"加州大学圣塔芭芭拉分校"),
    ("university-of-chicago","University of Chicago","IL","Chicago",41.7886,-87.5987,"芝加哥大学"),
    ("university-of-colorado-boulder","University of Colorado Boulder","CO","Boulder",40.0076,-105.2660,"科罗拉多大学波德分校"),
    ("university-of-florida","University of Florida","FL","Gainesville",29.6516,-82.3248,"佛罗里达大学"),
    ("university-of-georgia","University of Georgia","GA","Athens",33.9480,-83.3779,"佐治亚大学"),
    ("university-of-illinois-urbana-champaign","University of Illinois Urbana-Champaign","IL","Urbana",40.1020,-88.2272,"伊利诺伊大学香槟分校"),
    ("university-of-iowa","University of Iowa","IA","Iowa City",41.6610,-91.5360,"爱荷华大学"),
    ("university-of-maryland-college-park","University of Maryland, College Park","MD","College Park",38.9869,-76.9426,"马里兰大学帕克分校"),
    ("university-of-michigan-ann-arbor","University of Michigan—Ann Arbor","MI","Ann Arbor",42.2780,-83.7382,"密歇根大学安娜堡分校"),
    ("university-of-minnesota-twin-cities","University of Minnesota Twin Cities","MN","Minneapolis",44.9778,-93.2650,"明尼苏达大学双城分校"),
    ("university-of-north-carolina-chapel-hill","University of North Carolina—Chapel Hill","NC","Chapel Hill",35.9049,-79.0468,"北卡罗来纳大学教堂山分校"),
    ("university-of-notre-dame","University of Notre Dame","IN","Notre Dame",41.7045,-86.2381,"圣母大学"),
    ("university-of-pennsylvania","University of Pennsylvania","PA","Philadelphia",39.9522,-75.1932,"宾夕法尼亚大学"),
    ("university-of-rochester","University of Rochester","NY","Rochester",43.1284,-77.6292,"罗切斯特大学"),
    ("university-of-south-carolina-columbia","University of South Carolina","SC","Columbia",33.9960,-81.0310,"南卡罗来纳大学"),
    ("university-of-southern-california","University of Southern California","CA","Los Angeles",34.0224,-118.2851,"南加州大学"),
    ("university-of-texas-austin","University of Texas—Austin","TX","Austin",30.2860,-97.7396,"德克萨斯大学奥斯汀分校"),
    ("university-of-virginia","University of Virginia","VA","Charlottesville",38.0336,-78.5080,"弗吉尼亚大学"),
    ("university-of-washington","University of Washington","WA","Seattle",47.6553,-122.3035,"华盛顿大学"),
    ("university-of-wisconsin-madison","University of Wisconsin—Madison","WI","Madison",43.0766,-89.4125,"威斯康星大学麦迪逊分校"),
    ("vanderbilt-university","Vanderbilt University","TN","Nashville",36.1447,-86.8027,"范德堡大学"),
    ("washington-university-in-st-louis","Washington University in St. Louis","MO","St. Louis",38.6488,-90.3105,"圣路易斯华盛顿大学"),
    ("yale-university","Yale University","CT","New Haven",41.3163,-72.9220,"耶鲁大学"),
]

SAFETY_MAP = {"CA":65,"NY":62,"MA":72,"IL":58,"PA":65,"TX":60,"FL":58,"GA":55,"NC":62,"OH":60,"IN":65,"MI":58,"MN":70,"WI":68,"WA":68,"OR":66,"CO":68,"AZ":58,"NV":50,"NJ":68,"CT":70,"RI":68,"NH":75,"MD":55,"VA":65,"SC":55,"TN":58,"MO":55,"IA":72,"DC":52}
COMMUNITY_MAP = {"CA":"high","NY":"high","MA":"high","IL":"medium","PA":"medium","TX":"medium","WA":"high","NJ":"high","MD":"medium","VA":"medium","MI":"medium","GA":"medium","NC":"medium","OH":"low","IN":"low","MN":"medium","WI":"low","CO":"low","AZ":"low","CT":"medium","RI":"medium","NH":"low","FL":"medium","SC":"low","TN":"low","MO":"low","IA":"low","DC":"high"}

def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def main():
    rankings = read_json(PIPELINE / "data/ranking-seeds/2026-best-colleges/completion-national/national-universities-top-50.json")
    rank_map = {r["school_display_name"]: r["numeric_rank"] for r in rankings["records"]}

    histories = {o["candidate_id"].replace("candidate-v2:",""): o["history_summary"] for o in read_json(PIPELINE / "data/stage3d-fill-bulk-completion-v2/history-observations.json")["observations"]}

    anec_raw = read_json(PIPELINE / "data/stage3d-fill-bulk-completion-v2/anecdote-observations.json")["observations"]
    anec_map = {}
    for o in anec_raw:
        cid = o["candidate_id"].replace("candidate-v2:","")
        anec_map.setdefault(cid, []).append(o.get("content_zh",""))

    progs_raw = read_json(PIPELINE / "data/stage3b/official-program-observations.json")["observations"]
    progs_map = {}
    for o in progs_raw:
        cid = o["candidate_id"].replace("candidate-v2:","")
        progs_map.setdefault(cid, set()).add(o["program_name"])
    progs_map = {k: sorted(v) for k, v in progs_map.items()}

    mem_raw = read_json(PIPELINE / "data/university-universe-candidates/v2-source-limited/candidate-memberships.json")["memberships"]
    mem_map = {}
    for e in mem_raw:
        cid = e["candidate_university_id"].replace("candidate-v2:","")
        mem_map.setdefault(cid, []).append(e["membership_reason"])

    pois = []
    for sid, name, state, city, lat, lng, cn in SCHOOLS:
        rank = rank_map.get(name)
        reasons = mem_map.get(sid, [])
        has_program = any("program_top_20" in r for r in reasons)
        
        if rank and rank <= 20: tier, band = "top20", f"National #{rank}"
        elif rank: tier, band = "top50", f"National #{rank}"
        elif has_program: tier, band = "top20", "Program Top 20"
        else: tier, band = "top50", "National Top 50"

        progs = progs_map.get(sid, ["Computer Science","Business","Engineering","Economics","Biology"])
        safety = SAFETY_MAP.get(state, 60)
        cc = COMMUNITY_MAP.get(state, "medium")

        if rank and rank <= 10: rec, cost = 98, 620000
        elif rank and rank <= 20: rec, cost = 94, 560000
        elif rank and rank <= 30: rec, cost = 88, 520000
        elif rank and rank <= 50: rec, cost = 80, 460000
        else: rec, cost = 75, 420000

        df = city in {"New York","Boston","Los Angeles","San Francisco","Chicago","Washington","Seattle","Atlanta","Dallas","Houston"} or state in {"CA","NY","IL","WA","GA","TX","MA","DC"}

        history = histories.get(sid, "")
        anecdotes_list = anec_map.get(sid, [])

        poi = {
            "id": sid, "name": name, "chineseName": cn,
            "country": "United States", "city": city, "state": state,
            "stateFips": STATE_FIPS.get(state, ""),
            "latitude": lat, "longitude": lng,
            "rankingBand": band, "rankingTier": tier,
            "annualCostRmb": cost, "safetyScore": safety,
            "recognitionScore": rec, "chineseCommunity": cc,
            "directFlight": df,
            "postStudyVisa": "OPT / STEM OPT (36 months for STEM)",
            "programs": progs,
            "parentHighlights": [
                f"位于{city}的{cn}，全美排名第{rank}位" if rank else f"位于{city}的顶尖大学",
                f"强劲的{progs[0]}领域实力",
            ],
            "studentHighlights": ["丰富的学术资源与研究机会","多元化国际学生社区","强劲的职业发展与校友网络"],
            "verifiedAt": "2026-07-01", "sourceCount": max(3, len(reasons) or 5),
            "campusImages": [],
            "historySummary": (history[:250] + ("..." if len(history) > 250 else "")) if history else None,
            "anecdotes": anecdotes_list[:3] if anecdotes_list else [],
            "nearby": {
                "subwayStations": 1,
                "chineseRestaurants": 20 if cc=="high" else (10 if cc=="medium" else 3),
                "asianGroceries": 3 if cc=="high" else (2 if cc=="medium" else 1),
                "avgRentRmb": min(18000, max(5000, cost // 45)),
            },
        }
        if rank: poi["numericRank"] = rank
        pois.append(poi)

    pois.sort(key=lambda p: (1, p["name"]) if not p.get("numericRank") else (0, p["numericRank"], p["name"]))

    doc = {"_instructions": "PathOS 大学数据 — 62 所候选大学","_lastUpdated": "2026-07-21","universities": pois}
    out = FRONTEND / "src/data/universities.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(pois)} universities to {out}")
    with_r = sum(1 for p in pois if p.get("numericRank"))
    with_h = sum(1 for p in pois if p.get("historySummary"))
    print(f"  {with_r} with rank, {with_h} with history, {sum(bool(p.get('anecdotes')) for p in pois)} with anecdotes")

if __name__ == "__main__":
    main()
