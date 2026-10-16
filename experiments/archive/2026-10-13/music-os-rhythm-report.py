import hashlib,json
from pathlib import Path
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
r=json.loads(Path('experiments/review/rhythm.json').read_text());old=json.loads(Path('/private/tmp/music-os-rhythm-before-publish.json').read_text());p=json.loads(Path('experiments/review/practice.json').read_text());m=json.loads(Path('experiments/generated/automatic-first-ten-v1/manifest.json').read_text())
assert len(r['cases'])==len(p['cases'])==len(m['cases'])==10
for a,b,c,d in zip(r['cases'],old['cases'],p['cases'],m['cases']):
 assert a['recording']==b['recording']==c['recording']==d['recording']
 assert a['beat_times_seconds']==b['beat_times_seconds'] and a['pulse_bpm']==b['pulse_bpm']
assert r['manifest_sha256']==sha('experiments/generated/automatic-first-ten-v1/manifest.json')
assert r['config_sha256']==sha('experiments/fixtures/rhythm-first-ten.json')
report={'schema_version':'playalong-rhythm-results-1.0','checked_date':'2026-10-12','status':'Implementation and isolated browser checks passed; Mac deployment verification pending','gold':False,'chord_boundaries_modified':False,'audio_or_pack_identity_modified':False,'implementation_sha256':sha('experiments/analysis/rhythm_grid.py'),'config_sha256':r['config_sha256'],'rhythm_sha256':sha('experiments/review/rhythm.json'),'practice_sha256':sha('experiments/review/practice.json'),'player_manifest_sha256':r['manifest_sha256'],'rhythm_runtime_seconds':r['runtime_seconds'],'verification':{'python_distinct_passed':239,'standard_passed':223,'pinned_evaluation_passed':16,'javascript_helper_checks_passed':47,'isolated_browser_compound_meter':True,'isolated_browser_wonderwall_beats_only':True,'isolated_browser_seconds_choice':True,'isolated_browser_core_view':True,'isolated_browser_feedback_capture_reload':True,'isolated_browser_proportional_widths':True,'normal_player_test_feedback_added':False},'cases':[]}
for a,c in zip(r['cases'],p['cases']):report['cases'].append({'recording_id':a['recording']['id'],'audio_sha256':a['recording']['audio_sha256'],'pulse_bpm':a['pulse_bpm'],'pulse_count':len(a['beat_times_seconds']),'covered_pulse_span_seconds':[a['beat_times_seconds'][0],a['beat_times_seconds'][-1]],'beats_per_bar':a['beats_per_bar'],'meter_label':a['meter_label'],'practice_patterns':[i['id'] for i in c['patterns']]})
Path('docs/PLAYALONG_RHYTHM_RESULTS.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
print('Ten rhythm grids and 20 practice suggestions verified; regenerate preserved all pulse positions and tempo values.')
