import zipfile, csv, io, json, re

with open('/Users/coco/Desktop/pathos/frontend/src/data/universities.json') as f:
    frontend = json.load(f)

# Build matching from scorecard
zf = zipfile.ZipFile('/Users/coco/Desktop/pathos/data-pipeline/stage3b-official/Most-Recent-Cohorts-Institution_05192025.zip')
content = zf.read('Most-Recent-Cohorts-Institution_05192025.csv').decode('utf-8')
reader = csv.DictReader(io.StringIO(content))
all_rows = list(reader)

score_by_name = {}
for row in all_rows:
    instnm = row.get('INSTNM', '').strip()
    nm = instnm.lower().strip()
    nm = re.sub(r'[,\-—–]', ' ', nm)
    nm = re.sub(r'\s+', ' ', nm).strip()
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

# Match frontend to scorecard
matches = {}
for uni in frontend['universities']:
    fe_name = normalize(uni['name'])
    if fe_name in score_by_name:
        matches[uni['id']] = score_by_name[fe_name]
        continue
    best = 0
    best_row = None
    for sc_name, row in score_by_name.items():
        sc_n = normalize(sc_name)
        fe_words = set(fe_name.split())
        sc_words = set(sc_n.split())
        if len(fe_words) == 0 or len(sc_words) == 0:
            continue
        overlap = len(fe_words & sc_words)
        total = len(fe_words | sc_words)
        ratio = overlap / total
        if ratio > 0.5 and ratio > best:
            best = ratio
            best_row = row
    if best_row:
        matches[uni['id']] = best_row
    else:
        print(f'NO MATCH: {uni["name"]}')

print(f'Matched: {len(matches)}/62')

# Extract median earnings and normalize
earnings = []
for uid, row in matches.items():
    val = row.get('MD_EARN_WNE_P10', '') or row.get('MD_EARN_WNE_P6', '')
    if val and val.strip():
        try:
            e = float(val.strip())
            earnings.append((uid, e))
        except:
            pass

if earnings:
    vals = [e for _, e in earnings]
    min_e, max_e = min(vals), max(vals)
    print(f'Earnings range: ${min_e:.0f} - ${max_e:.0f}')
    
    # Normalize: scale to 0-100 with $30K bottom anchor
    bottom = 30000
    top = max_e + 10000  # give some headroom
    
    count = 0
    for uid, e in earnings:
        score = (e - bottom) / (top - bottom) * 100
        score = max(0, min(100, round(score)))
        # Find and update frontend university
        for uni in frontend['universities']:
            if uni['id'] == uid:
                uni['employmentScore'] = score
                count += 1
                break
    
    print(f'Updated employmentScore: {count} universities')
    # Show some samples
    print(f'\nSample values:')
    top5 = sorted(earnings, key=lambda x: -x[1])[:3]
    for uid, e in top5:
        for uni in frontend['universities']:
            if uni['id'] == uid:
                print(f'  {uni["name"]}: ${e:.0f} → score {uni["employmentScore"]}')
    
frontend['_lastUpdated'] = '2026-07-22'
with open('/Users/coco/Desktop/pathos/frontend/src/data/universities.json', 'w', encoding='utf-8') as f:
    json.dump(frontend, f, ensure_ascii=False, indent=2)
print('\nSaved.')
