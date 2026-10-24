"""Refresh income from the newest NTA economic workbook linked by NYC Planning.

Uses only Python's standard library. Validates the release, fields, and exact
residential NTA2020 codes before replacing the last validated snapshot.
"""
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import re
import time
import urllib.request
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CATALOG = 'https://apps.nyc.gov/content-api/v1/content/planning/resources/datasets/american-community-survey'
GEOGRAPHY = 'https://data.cityofnewyork.us/resource/9nt8-h7nd.geojson?$limit=1000'
NS = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def fetch(url):
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': 'NYC-Youth-Asthma-income-refresh/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def worksheet(archive, path):
    strings = []
    if 'xl/sharedStrings.xml' in archive.namelist():
        strings = [''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('s:si', NS)]
    rows = []
    for row in ET.fromstring(archive.read(path)).findall('.//s:row', NS):
        values = {}
        for cell in row.findall('s:c', NS):
            value = cell.find('s:v', NS)
            if value is not None:
                text = strings[int(value.text)] if cell.attrib.get('t') == 's' else value.text
            elif cell.attrib.get('t') == 'inlineStr':
                text = ''.join(cell.find('s:is', NS).itertext())
            else:
                continue
            values[re.sub(r'\d', '', cell.attrib['r'])] = text
        rows.append(values)
    return rows


def number(raw):
    try:
        n = float(raw)
        return n if n >= 0 else None
    except (ValueError, TypeError):
        return None


def extract(workbook, year, url):
    with zipfile.ZipFile(io.BytesIO(workbook)) as archive:
        sheets = ET.fromstring(archive.read('xl/workbook.xml')).findall('s:sheets/s:sheet', NS)
        rels = {r.attrib['Id']: r.attrib['Target'].lstrip('/') for r in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        paths = {}
        for sheet in sheets:
            target = rels[sheet.attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
            paths[sheet.attrib['name']] = target if target.startswith('xl/') else 'xl/' + target
        about = ' '.join(str(v) for row in worksheet(archive, paths['About']) for v in row.values())
        assert f'{year-4}-{year} ACS' in about, 'Workbook reference period does not match catalog release'
        rows = worksheet(archive, paths['EconData'])
    header = rows[0]
    records = [{header[k]: v for k, v in row.items() if k in header} for row in rows[1:]]
    required = {'GeoType', 'GeoID', 'GeogName', 'Borough', 'NTAType', 'MdHHIncE', 'MdHHIncM'}
    assert required.issubset(set(header.values())), 'Source schema changed'
    result = []
    for row in records:
        if row.get('GeoType') != 'NTA2020' or row.get('NTAType') != '0':
            continue
        assert re.fullmatch(r'(BX|BK|MN|QN|SI)\d{4}', row['GeoID']), 'Unexpected NTA code'
        value = number(row.get('MdHHIncE'))
        result.append({
            'NTA_Code': row['GeoID'], 'NTA_Name': row['GeogName'], 'Borough': row['Borough'],
            'Median_Household_Income': value, 'Income_MOE_90': number(row.get('MdHHIncM')),
            'Income_Raw_Estimate': row.get('MdHHIncE'),
            'Income_Data_Status': 'ACS survey estimate' if value is not None else 'Unavailable in source',
            'Income_Reference_Period': f'{year-4}–{year}', 'Income_Dollar_Year': year,
            'Income_Geography': 'NTA2020', 'Income_Source_URL': url,
            'Income_Source': 'U.S. Census Bureau ACS, compiled by NYC Department of City Planning',
        })
    assert len(result) == len({r['NTA_Code'] for r in result}) and len(result) >= 190, 'Duplicate or incomplete residential NTA coverage'
    assert sum(r['Median_Household_Income'] is not None for r in result) >= len(result)*0.95, 'Income estimate coverage dropped'
    return sorted(result, key=lambda r: r['NTA_Code'])


def main():
    description = json.loads(fetch(CATALOG))['description']
    links = re.findall(r'https://s-media\.nyc\.gov/[^\s"<>]+/Econ_(\d{4})ACS5YR_NTA\.xlsx', description)
    assert links, 'No current official NTA economic workbook in catalog'
    year = max(map(int, links))
    url = re.search(r'https://s-media\.nyc\.gov/[^\s"<>]+/Econ_' + str(year) + r'ACS5YR_NTA\.xlsx', description)[0]
    workbook = fetch(url)
    rows = extract(workbook, year, url)
    geography = json.loads(fetch(GEOGRAPHY))
    codes = {f['properties']['nta2020'] for f in geography['features'] if f['properties']['ntatype'] == '0'}
    assert codes == {r['NTA_Code'] for r in rows}, 'Income and published NTA2020 boundary codes differ'
    output = ROOT / 'data/income_latest.json'
    if output.exists():
        previous = json.loads(output.read_text())
        assert year >= previous['release_year'], 'Refusing to replace a newer release with an older one'
    payload = {
        'release_year': year, 'reference_period': f'{year-4}–{year}', 'dollar_year': year,
        'geography': 'NTA2020', 'source_url': url, 'catalog_url': CATALOG,
        'geography_url': GEOGRAPHY, 'source_sha256': hashlib.sha256(workbook).hexdigest(),
        'checked_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'refresh_schedule': 'Daily', 'rows': rows,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_suffix('.tmp')
    staging.write_text(json.dumps(payload, ensure_ascii=False, separators=(',', ':')) + '\n')
    staging.replace(output)
    stream = io.StringIO()
    csv_rows = [dict(row, Income_Checked_At=payload['checked_at'], Income_Source_SHA256=payload['source_sha256']) for row in rows]
    writer = csv.DictWriter(stream, fieldnames=csv_rows[0])
    writer.writeheader()
    writer.writerows(csv_rows)
    (ROOT / 'data/income_latest.csv').write_text(stream.getvalue())
    print(f'Validated ACS {year-4}–{year}: {len(rows)} exact residential NTA2020 matches')


if __name__ == '__main__':
    main()
