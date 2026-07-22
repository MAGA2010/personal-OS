import zipfile, csv, io, json, re

# 1. Read frontend
with open('/Users/coco/Desktop/pathos/frontend/src/data/universities.json') as f:
    frontend = json.load(f)

# 2. Pipeline UNITID mapping
with open('/Users/coco/Desktop/pathos/data-pipeline/artifacts/stage3-program-mvp-detail-pack/program-mvp-universities.json') as f:
    pipeline = json.load(f)

fe_id_to_pipeline = {}
for u in pipeline['universities']:
    cid = u['candidate_id']
    fe_id = cid.replace('candidate-v2:', '')
    fe_id_to_pipeline[fe_id] = {'name': u['display_name'], 'unitid': str(u.get('unitid', '')) if u.get('unitid') else None}

with_unitid = sum(1 for v in fe_id_to_pipeline.values() if v['unitid'])
print(f'Pipeline with UNITID: {with_unitid}/62')

# 3. Read Scorecard
zf = zipfile.ZipFile('/Users/coco/Desktop/pathos/data-pipeline/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip')
content = zf.read('Most-Recent-Cohorts-Institution_05192025.csv').decode('utf-8')
reader = csv.DictReader(io.StringIO(content))

all_rows = list(reader)
print(f'Scorecard rows: {len(all_rows)}')

score_by_unitid = {}
score_by_name = {}
for row in all_rows:
    uid = row.get('UNITID', '').strip()
    instnm = row.get('INSTNM', '').strip()
    # Normalize name
    nm = instnm.lower().strip()
    nm = re.sub(r'[,\-—–]', ' ', nm)
    nm = re.sub(r'\s+', ' ', nm).strip()
    if uid:
        score_by_unitid[uid] = row
    if instnm:
        score_by_name[nm] = row

def normalize(s):
    s = s.lower().strip()
    s = s.replace('—', ' ').replace('–', ' ').replace(',', ' ').replace('-', ' ')
    s = re.sub(r'[^a-z0-9\s&\/]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    for suf in [' main campus', ' main', ' twin cities', 'all campuses']:
        if s.endswith(suf):
            s = s[:-len(suf)]
    return s

# Match
matches = {}
for uni in frontend['universities']:
    fe_id = uni['id']
    pipe_info = fe_id_to_pipeline.get(fe_id)
    if pipe_info and pipe_info['unitid'] and pipe_info['unitid'] in score_by_unitid:
        matches[fe_id] = score_by_unitid[pipe_info['unitid']]
        continue
    # Name match
    fe_name = normalize(uni['name'])
    if fe_name in score_by_name:
        matches[fe_id] = score_by_name[fe_name]
        continue
    # Fuzzy
    best_score, best_row = 0, None
    for sc_name, row in score_by_name.items():
        sc_n = normalize(sc_name)
        fe_words = set(fe_name.split())
        sc_words = set(sc_n.split())
        overlap = len(fe_words & sc_words)
        total = len(fe_words | sc_words)
        if total > 0 and overlap / total > 0.5 and overlap / total > best_score:
            best_score = overlap / total
            best_row = row
    if best_row:
        matches[fe_id] = best_row

print(f'Matched: {len(matches)}/62')
missing = [u['name'] for u in frontend['universities'] if u['id'] not in matches]
for m in missing:
    print(f'  MISS: {m}')

# Update admissionRate
adm = 0
for uni in frontend['universities']:
    if uni['id'] not in matches:
        continue
    row = matches[uni['id']]
    val = row.get('ADM_RATE', '') or row.get('ADM_RATE_ALL', '')
    if val and val.strip():
        try:
            rate = float(val.strip())
            if 0 <= rate <= 1:
                uni['admissionRate'] = round(rate * 100, 1)
                adm += 1
        except:
            pass
print(f'Updated admissionRate: {adm}/62')

still = [u['name'] for u in frontend['universities'] if not u.get('admissionRate')]
print(f'Still missing: {len(still)}')

frontend['_lastUpdated'] = '2026-07-22'
with open('/Users/coco/Desktop/pathos/frontend/src/data/universities.json', 'w', encoding='utf-8') as f:
    json.dump(frontend, f, ensure_ascii=False, indent=2)
print('Saved.')
