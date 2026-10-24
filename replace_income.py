"""Extract published NYC Planning NTA2010 income estimates without aggregating medians."""
import csv
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).parent
SOURCE = 'https://www.nyc.gov/assets/planning/download/office/planning-level/nyc-population/acs/econ_2018_acs5yr_nta.xlsx'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
with zipfile.ZipFile(ROOT / 'econ2018.xlsx') as z:
    strings = [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si', NS)]
    rows = []
    for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).findall('.//s:row', NS):
        values = {}
        for cell in row.findall('s:c', NS):
            v = cell.find('s:v', NS)
            if v is not None:
                values[re.sub(r'\d', '', cell.attrib['r'])] = strings[int(v.text)] if cell.attrib.get('t') == 's' else v.text
        rows.append(values)
    headers = rows[0]
    records = [{headers[k]: v for k, v in row.items() if k in headers} for row in rows[1:] if row.get('A') == 'NTA2010']

def amount(raw):
    try:
        value = float(raw)
        return round(value) if value >= 0 else None
    except (ValueError, TypeError):
        return None

income = []
for record in records:
    raw = record.get('MdHHIncE')
    value = amount(raw)
    income.append(dict(
        NTA_Code=record['GeoID'], NTA_Name=record['GeogName'],
        Median_Household_Income=value,
        Income_MOE_90=amount(record.get('MdHHIncM')),
        Income_Raw_Estimate=raw,
        Income_Data_Status='ACS survey estimate' if value is not None else 'Unavailable in source',
        Income_Source='U.S. Census Bureau ACS, compiled by NYC Department of City Planning',
        Income_Source_URL=SOURCE, Income_Reference_Period='2014–2018',
        Income_Dollar_Year='2018', Income_Geography='NTA2010',
        Income_Source_Field='MdHHIncE', Income_MOE_Field='MdHHIncM',
        Income_Retrieved='2026-10-23',
        Income_Source_SHA256=hashlib.sha256((ROOT / 'econ2018.xlsx').read_bytes()).hexdigest(),
    ))
assert len(income) == len({x['NTA_Code'] for x in income}) == 195
assert all(re.fullmatch(r'(BX|BK|MN|QN|SI)\d{2}', x['NTA_Code']) for x in income)
with (ROOT / 'income_acs_2014_2018_nta2010.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=income[0].keys())
    writer.writeheader()
    writer.writerows(income)

s = (ROOT / 'index.html').read_text()
# Remove every legacy income input. Preserve other layers for the separate source audit.
match = re.search(r'const MASTER_DATA = (\[.*?\]);', s)
master = json.loads(match[1])
for row in master:
    row['Median_Household_Income'] = None
    row['Working_Class_Score'] = None
    row['Working_Class_Classification'] = 'Unavailable pending input verification'
s = s[:match.start(1)] + json.dumps(master) + s[match.end(1):]
s = s.replace('const SOURCES = {', 'const INCOME_SOURCE_ROWS = ' + json.dumps(income, ensure_ascii=False) + ';\nconst INCOME_BY_NTA = new Map(INCOME_SOURCE_ROWS.map(row => [row.NTA_Code, row]));\n\nconst SOURCES = {')
s = s.replace('income: 82000', 'income: null')
s = re.sub(r'income:(52000|76000|104000|79000|91000)', 'income:null', s)
s = re.sub(r'profile.income \*= [\d.]+; ', '', s)
s = s.replace('  profile.income = Math.round(clamp(profile.income, 32000, 165000));', '')
# Override all income and dependent score paths after row creation, using exact codes only.
s = s.replace('completeData.set(code, makeCompleteRow(f));', '''const row = makeCompleteRow(f);
    const source = INCOME_BY_NTA.get(code);
    Object.assign(row, source || {
      Median_Household_Income: null, Income_MOE_90: null,
      Income_Data_Status: 'No exact NTA2010 code match',
      Income_Reference_Period: '2014–2018', Income_Geography: 'NTA2010'
    });
    // Preserve the map's display name. The code is the only join key.
    row.NTA_Name = getNtaName(f);
    row.Working_Class_Score = null;
    row.Working_Class_Classification = 'Unavailable pending input verification';
    completeData.set(code, row);''')
s = s.replace('<option value="Working_Class_Score">Working-class score</option>', '<option value="Working_Class_Score" disabled>Working-class score (pending verification)</option>')
s = s.replace('<p>Values are labeled as <span class="badge">Observed/source data</span> to distinguish source data from gap-filled estimates.</p>', '<p>Income: ACS 2014–2018 survey estimates in 2018 dollars, joined by exact NTA2010 code. Other demographic layers still contain unverified starter/generated values.</p>')
start = s.index('    <strong>What working class means:</strong>')
end = s.index('\n  </div>', start)
s = s[:start] + '''    <strong>Income source:</strong> U.S. Census Bureau, 2014–2018 American Community Survey, compiled by NYC Planning for NTA2010. Median annual household income is expressed in 2018 inflation-adjusted dollars. Hover or click to see the 90% margin of error. <a href="''' + SOURCE + '''">Download the official source</a>. <a href="INCOME_SOURCES.md">Source and matching notes</a>. Income uses exact NTA2010 codes; missing values are not filled. The working-class score is unavailable while poverty and education inputs await verification. Income and asthma periods may differ; this map does not establish an income–asthma relationship.''' + s[end:]
s = s.replace('then review the rankings to see which neighborhoods may need closer public-health attention.', 'then review the descriptive rankings. Income is documented; the other demographic layers remain provisional.')
s = s.replace('Median household income</option>', 'Median household income (ACS 2014–2018)</option>')
s = s.replace("Median_Household_Income: 'Median household income'", "Median_Household_Income: 'Median household income (ACS 2014–2018, 2018 dollars)'")
s = s.replace("'Median_Household_Income',\n", "'Median_Household_Income',\n      " + ','.join(repr(k) for k in income[0] if k.startswith('Income_')) + ',\n')
s = s.replace('<div class="tt-row"><span>Poverty rate</span>', '''<div class="tt-row"><span>Income 90% margin of error</span><span class="tt-val">${demo && Number.isFinite(numeric(demo.Income_MOE_90)) ? '±' + money(numeric(demo.Income_MOE_90)) : '—'}</span></div>
    <div class="tt-row"><span>Income period / dollars</span><span class="tt-val">2014–2018 / 2018 dollars</span></div>
    <div class="tt-row"><span>Income source / geography</span><span class="tt-val">Census ACS / NYC Planning · NTA2010</span></div>
    <div class="tt-row"><span>Income status</span><span class="tt-val">${demo ? esc(demo.Income_Data_Status) : 'Unavailable'}</span></div>
    <div class="tt-row"><span>Other demographics</span><span class="tt-val">Unverified starter/generated values</span></div>
    <div class="tt-row"><span>Poverty rate</span>''')
s = s.replace('<span>Data status</span>', '<span>Asthma data status</span>')
s = s.replace('<div class="legend-foot"><span>Source: NYC neighborhoods</span>', '<div class="legend-foot"><span id="legendSourceText">Source information appears above</span>')
s = s.replace('function updateLegend() {', '''function updateLegend() {
  setTextSafe('legendSourceText', selectedLayer === 'Median_Household_Income'
    ? 'Source: Census ACS / NYC Planning, 2014–2018, 2018 dollars, NTA2010. Gray: no published estimate.'
    : selectedLayer.includes('Asthma') ? 'Asthma: NYC Health EHDP where matched; check neighborhood status for fallback values.'
    : 'Provisional: unverified starter/generated demographic values.');''')
s = s.replace('demographic context remains starter/modeled where ACS values are not embedded.', 'income is ACS 2014–2018 on NTA2010; other demographic context remains unverified starter/modeled.')
s = s.replace('demographic context uses starter rows plus modeled estimates for gaps.', 'income uses ACS 2014–2018 NTA2010 estimates; other demographics remain unverified.')
(ROOT / 'index.html').write_text(s)
print('Extracted', len(income), 'NTA2010 rows;', sum(x['Median_Household_Income'] is not None for x in income), 'published income estimates')
print('Examples:', [(x['NTA_Code'], x['NTA_Name'], x['Median_Household_Income'], x['Income_MOE_90']) for x in income if x['NTA_Code'] in ['MN33','MN34','BX39']])
