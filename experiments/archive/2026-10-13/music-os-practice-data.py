import json
from pathlib import Path
root=Path('/private/tmp/music-os-plan-20261010');manifest=json.loads((root/'experiments/generated/automatic-first-ten-v1/manifest.json').read_text())
config={'schema_version':'playalong-rhythm-config-1.0','status':'Curated pulse and meter hypotheses, not exact-upload timing gold','recordings':{}}
patterns={'schema_version':'playalong-practice-1.0','status':'Original project practice suggestions; not transcriptions of recorded strumming','cases':[]}
priors={
 'radiohead-creep-youtube-20261010':(93,80,105,'https://drumeoblog.s3.amazonaws.com/beat/wp-content/uploads/2021/11/08134434/15.-Creep.pdf'),
 'oasis-wonderwall-youtube-20261010':(88,78,98,'https://www.musicnotes.com/sheetmusic/oasis/wonderwall/MN0053372'),
 'animals-house-rising-sun-official-20261011':(78,65,90,'https://www.jonmaclennan.com/blog/house-of-the-rising-sun-guitar-lesson'),
 'white-stripes-seven-nation-army-youtube-20261011':(124,105,145,'https://bypass.drumscore.com/sheet-music/browse-by-artist/score/12768-the-white-stripes-7-nation-army-drum-sheet-music-tab'),
 'nirvana-come-as-you-are-youtube-20261011':(120,100,140,'https://www.musicnotes.com/sheetmusic/nirvana/come-as-you-are/MN0069767'),
 'van-morrison-brown-eyed-girl-youtube-20261011':(151,130,175,'https://drumscore.com/sheet-music/browse-by-artist/score/14285-van-morrison-brown-eyed-girl-drum-sheet-music-tab'),
 'beatles-twist-and-shout-youtube-20261011':(123,105,145,'https://www.drumscore.com/sheet-music/browse-by-artist/score/14622-the-beatles-twist-and-shout'),
 'bob-dylan-knockin-heavens-door-youtube-20261011':(70,50,100,'https://www.jonmaclennan.com/blog/knockin-on-heaven%27s-door-chords'),
}
for c in manifest['cases']:
 id=c['id']; house=id.startswith('animals-house'); wonder=id.startswith('oasis-wonder'); riff=id.startswith(('nirvana-','white-stripes-'))
 cfg={'start_bpm':120,'beats_per_bar':4,'meter_label':'4/4 assumed','meter_status':'Four-quarter practice convention; recording bar structure unverified','pulse_unit':'quarter note (proposed)'}
 if id in priors:
  bpm,low,high,url=priors[id];cfg.update(start_bpm=bpm,tempo_min_bpm=low,tempo_max_bpm=high,source_url=url,pulse_prior_status='Source-informed range; audio chooses tempo within it; not timing gold')
 else: cfg['pulse_prior_status']='Default tracker prior; metrical level unverified'
 if id.startswith('bob-dylan-'):cfg['pulse_prior_status']='Project slow-ballad pulse proposal informed by teacher setup; exact BPM unverified'
 if wonder:
  cfg.update(beats_per_bar=None,meter_label='Beat count; meter varies',meter_status='Sources describe 4/4 and 2/4; local meter transitions unverified',additional_source_url='https://bypass.drumscore.com/sheet-music/browse-by-artist/score/952-oasis-wonderwall-drum-sheet-music-tab')
 if house:
  cfg.update(beats_per_bar=2,meter_label='6/8 · 2 dotted-quarter beats per bar',meter_status='Source 6/8; two dotted-quarter pulse convention is a project hypothesis',pulse_unit='dotted quarter (proposed)',pulse_prior_status='Project-selected dotted-quarter level from meter plus acoustic diagnostic; source does not establish BPM')
 config['recordings'][id]=cfg
 first={'id':'steady-down','name':'Start: steady downstrokes','counts':['1','2','3','4'],'strokes':['D','D','D','D'],'description':'Strum down on each count. Keep the motion steady and change shape when the chord cue changes.'}
 second={'id':'down-up','name':'Next: down and up','counts':['1','&','2','&','3','&','4','&'],'strokes':['D','U','D','U','D','U','D','U'],'description':'Add an upstroke between counts. Begin slowly; keep moving through chord changes.'}
 note='A starting rhythm exercise. The recording may use a different pattern or picking.'
 if wonder:
  second={'id':'syncopated','name':'Next: try syncopation','counts':['1','&','2','&','3','&','4','&'],'strokes':['D','—','D','U','—','U','D','U'],'description':'Keep your hand moving down and up; skip the marked strokes. This is a four-count exercise, not the complete recorded pattern.'}
  note='Four-count practice suggestion; the song has section and meter changes. Its exact strumming lesson still needs review.'
 if house:
  first={'id':'six-anchor','name':'Start: two gentle strums','counts':['1','2','3','4','5','6'],'strokes':['D','—','—','D','—','—'],'description':'Count six eighth notes. Strum gently on 1 and 4, then let the chord ring.'}
  second={'id':'six-motion','name':'Next: six-count motion','counts':['1','2','3','4','5','6'],'strokes':['D','U','D','U','D','U'],'description':'Keep six even strokes, gently stressing 1 and 4. The recorded arpeggio is a later exercise.'}
  note='6/8 practice suggestion: these six counts are eighth notes; one bar has two dotted-quarter beats. The recorded guitar uses arpeggios.'
 if riff:note='A strumming exercise for chord practice. The recorded part is mainly a riff; these arrows do not teach that riff.'
 if id.startswith('radiohead-'):note='Start with a steady chord exercise. The recorded verse also uses arpeggios; these arrows are a practice suggestion.'
 patterns['cases'].append({'recording':c['recording'],'meter_label':'6/8' if house else '4/4 practice','beats_description':'Count six eighth notes' if house else 'Count four beats; & is halfway between beats','patterns':[first,second],'status':'practice-suggestion','note':note})
(root/'experiments/fixtures/rhythm-first-ten.json').write_text(json.dumps(config,indent=2,ensure_ascii=False)+'\n')
(root/'experiments/review/practice.json').write_text(json.dumps(patterns,indent=2,ensure_ascii=False)+'\n')
print('Saved 10 pulse configurations and 20 original practice patterns; no detector outputs modified.')
