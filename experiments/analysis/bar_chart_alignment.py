"""Conditional timing from full written musical coordinates and audio only.

This small research prototype searches chart origin/tempo using acoustic fit.
Publisher wallclock annotations are isolated in scoring references. Full charts
are never clipped by reference times before inference or accepted for playback.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import wave

import numpy as np

import chart_aligner
from candidates import nnls_chroma_adapter
import guitarset_pilot as pilot
import jazzsamba_alignment_check as previous
import lab
import rhythm_grid

COMMIT = '3715097238b33593d865d05b772e094642843612'
BASE = f'https://raw.githubusercontent.com/pnlong/jazzsamba-demo/{COMMIT}/'
PICKS = ((3, 'development'), (2, 'holdout'), (6, 'holdout'))
CONDITIONS = ('source-musical-chart', 'wrong-root-plus-one-semitone', 'delete-written-bar-eight')
CANDIDATES = ('audio-selected-source-tempo-grid', 'audio-pulse-grid')
SETTINGS = {'tempo_factors': [round(.65 + index * .01, 2) for index in range(91)],
            'origin_quarter_note_steps': .25, 'origin_bar_radius': 2,
            'quarter_notes_per_detected_pulse': [.5, 1., 2.],
            'pulse_start_bpm': 'declared source quarter-note BPM; no prescribed pulse times',
            'pulse_tracker': 'unchanged librosa 0.9.2 onset beat_track, tightness 100, trim=True',
            'objective': 'Mean assigned-template cosine over every active NNLS frame; unknown/unsupported/gaps score zero; silence excluded',
            'tie_rule': 'Higher objective, then tempo factor nearest 1, then absolute musical origin nearest zero, then declaration order',
            'missing_bar': 8, 'boundary_tolerance_seconds': .15,
            'unknown_score': 'No confidence threshold or acceptance decision; predicted source unknowns remain X',
            'accepted_for_playback': False}
FORBIDDEN = {'start_time', 'end_time', 'time', 'start_seconds', 'end_seconds', 'timestamp', 'duration_seconds',
             'source_fields', 'reference', 'bars', 'bpm_from_reference'}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def save(path: Path, value: dict) -> None:
    chart_aligner.write_json_safely(path, value, [], overwrite=False)


def fetch(path: str, tree: dict, budget: int) -> tuple[bytes, dict]:
    entry = tree[path]
    if entry['size'] > budget:
        raise ValueError('Bounded acquisition refuses oversized publisher asset')
    with urllib.request.urlopen(BASE + path, timeout=30) as response:
        if response.status != 200:
            raise ValueError('Publisher asset did not return HTTP 200')
        raw = response.read(budget + 1)
    if len(raw) != entry['size'] or git_blob(raw) != entry['sha']:
        raise ValueError('Publisher Git-blob/size proof failed')
    return raw, {'url': BASE + path, 'path': path, 'bytes': len(raw), 'sha256': sha_bytes(raw), 'git_blob_sha1': entry['sha']}


def triad(row: dict) -> str:
    if row.get('is_no_chord') not in ('True', 'False'):
        raise ValueError('Explicit publisher no-chord field required')
    if row['is_no_chord'] == 'True':
        return 'N'
    # The declared easier target projects the supplied triad field, not a
    # guessed interpretation of the full altered/slash symbol.
    if row.get('triad') not in ('maj', 'min'):
        return 'X'
    root = row.get('root')
    if not isinstance(root, str) or not re.fullmatch(r'[A-G][#b]?', root):
        return 'X'
    return root + ':' + row['triad']


def coordinate(row: dict, prefix: str, meter: int) -> float:
    bar, fraction = float(row[prefix + '_bar']), float(row[prefix + '_fraction'])
    if not math.isfinite(bar) or not bar.is_integer() or bar < 0 or not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Invalid written bar/fraction coordinate')
    return (bar + fraction) * meter


def validate_chart(chart: dict) -> None:
    def inspect(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in FORBIDDEN or key.endswith('_seconds') or key.endswith('_timestamp'):
                    raise ValueError('Wallclock/reference field forbidden in musical model input: ' + key)
                inspect(child)
        elif isinstance(value, list):
            for child in value:
                inspect(child)
    inspect(chart)
    if chart.get('schema_version') != 'full-musical-chart-1.0':
        raise ValueError('Unsupported musical chart schema')
    if chart.get('quarter_notes_per_bar') not in (3, 4) or not 20 <= chart.get('declared_bpm', 0) <= 300:
        raise ValueError('This bounded prototype supports explicit 3/4 or 4/4 quarter-note meter and source BPM')
    rows = chart.get('positions')
    if not isinstance(rows, list) or not 1 <= len(rows) <= 2000:
        raise ValueError('Need a bounded full musical chart')
    previous_end = 0.
    for row in rows:
        start, end = row.get('start_quarter_note'), row.get('end_quarter_note')
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in (start, end)) or start < previous_end or end <= start:
            raise ValueError('Written positions must be ordered and nonoverlapping')
        label = row.get('label')
        if label not in ('N', 'X') and (not isinstance(label, str) or not re.fullmatch(r'[A-G][#b]?:(maj|min)', label)):
            raise ValueError('No guessed conversion of unsupported chord qualities')
        previous_end = end
    json.dumps(chart, allow_nan=False)


def musical_chart(annotation: dict, song: dict, identifier: str, annotation_sha: str) -> dict:
    meter_match = re.fullmatch(r'([34])/4', song['time_signature'])
    if not meter_match:
        raise ValueError('Meter is outside the predeclared quarter-note convention')
    meter = int(meter_match[1])
    rows, zero_extent, previous_end = [], [], 0.
    # Iterate ALL written chord rows. No wallclock field is accessed here, and
    # no row is selected according to its time in the 60-second recording.
    for source in annotation['chords']:
        start, end = coordinate(source, 'start', meter), coordinate(source, 'end', meter)
        if start < previous_end or end < start:
            raise ValueError('Invalid full written chart coordinate order')
        if end == start:
            # The publisher sometimes writes a terminal chord as a point with
            # no musical extent. Preserve that fact without inventing its hold.
            zero_extent.append({'quarter_note': start, 'source_symbol': source['chord'],
                                'label': triad(source), 'status': 'Unresolved zero written extent; no duration guessed'})
            continue
        if start > previous_end:
            rows.append({'start_quarter_note': previous_end, 'end_quarter_note': start, 'label': 'X', 'symbol_status': 'Unwritten gap'})
        rows.append({'start_quarter_note': start, 'end_quarter_note': end, 'label': triad(source),
                     'source_symbol': source['chord'], 'source_triad': source['triad']})
        previous_end = end
    chart = {'schema_version': 'full-musical-chart-1.0', 'recording_id': identifier,
             'declared_bpm': float(song['bpm']), 'quarter_notes_per_bar': meter,
             'coordinate_convention': 'Expanded publisher start_bar + start_fraction; bar zero retained, each 3/4 or 4/4 bar has 3 or 4 quarter notes',
             'source_annotation_sha256': annotation_sha, 'positions': rows,
             'condition': CONDITIONS[0], 'full_source_row_count': len(annotation['chords']),
             'unresolved_zero_extent_positions': zero_extent,
             'accepted_for_playback': False}
    validate_chart(chart)
    return chart


def condition_chart(chart: dict, condition: str) -> dict:
    if condition not in CONDITIONS:
        raise ValueError('Undeclared chart condition')
    result = copy.deepcopy(chart)
    result['condition'] = condition
    if condition == CONDITIONS[1]:
        for row in result['positions']:
            row['label'] = previous.corrupt_root(row['label'])
    elif condition == CONDITIONS[2]:
        meter = chart['quarter_notes_per_bar']
        left, right = SETTINGS['missing_bar'] * meter, (SETTINGS['missing_bar'] + 1) * meter
        if result['positions'][-1]['end_quarter_note'] <= right:
            raise ValueError('Full chart must contain the declared missing bar')
        rows = []
        for source in result['positions']:
            start, end = source['start_quarter_note'], source['end_quarter_note']
            if start < left:
                row = dict(source, end_quarter_note=min(end, left))
                if row['end_quarter_note'] > start:
                    rows.append(row)
            if end > right:
                row = dict(source, start_quarter_note=max(start, right) - meter, end_quarter_note=end - meter)
                if row['end_quarter_note'] > row['start_quarter_note']:
                    rows.append(row)
        result['positions'] = rows
    validate_chart(result)
    return result


def reference(annotation: dict, recording: dict) -> dict:
    # Explicit scoring-only producer: source wallclock values enter this
    # reference, never the musical chart consumed by infer().
    events = []
    for source in annotation['chords']:
        start, end = float(source['start_time']), float(source['end_time'])
        if not math.isfinite(start) or not math.isfinite(end):
            raise ValueError('Invalid publisher wallclock reference')
        if start >= recording['duration_seconds'] or end <= 0:
            continue
        if end <= start:
            raise ValueError('Invalid publisher wallclock interval inside scoring excerpt')
        events.append({'start_seconds': max(0., start), 'end_seconds': min(recording['duration_seconds'], end),
                       'label': triad(source), 'native_label': source['chord'], 'source_fields': source})
    result = {'schema_version': '1.0', 'recording': recording,
              'analysis': {'id': 'publisher-written-triad-reference', 'algorithm': 'dataset-reference', 'version': '1.0', 'runtime_seconds': 0},
              'chords': events}
    lab.validate_chart(result)
    return result


def pins() -> dict:
    files = ('experiments/analysis/bar_chart_alignment.py', 'experiments/analysis/jazzsamba_alignment_check.py',
             'experiments/analysis/chart_aligner.py', 'experiments/analysis/candidates/nnls_chroma_adapter.py',
             'experiments/analysis/rhythm_grid.py', 'experiments/analysis/guitarset_pilot.py',
             'experiments/analysis/guitarset_validation.py', 'experiments/analysis/alignment_screen.py',
             'experiments/candidate-assets/nnls-chroma-evidence-native/buildinfo.json',
             'experiments/candidate-assets/nnls-chroma-evidence-native/nnls-chroma-host',
             'experiments/candidate-assets/chordino-native/nnls-chroma.dylib')
    result = {name: pilot.sha(lab.ROOT / name) for name in files}
    if result['experiments/analysis/chart_aligner.py'] != previous.EXPECTED_FROZEN['experiments/analysis/chart_aligner.py'] or result['experiments/analysis/candidates/nnls_chroma_adapter.py'] != previous.EXPECTED_FROZEN['experiments/analysis/candidates/nnls_chroma_adapter.py']:
        raise ValueError('Prior frozen implementation changed')
    result['librosa_runtime'] = pilot.sha(lab.ROOT / '.venv-crema/lib/python3.11/site-packages/librosa/beat.py')
    return result


def prepare(output: Path) -> dict:
    if output.exists():
        raise ValueError('Use a fresh experiment directory')
    catalog_path = lab.ROOT / 'experiments/candidate-assets/jazzsamba-20261012/catalog.json'
    raw = catalog_path.read_bytes()
    if pilot.sha(catalog_path) != '396eb762880a4081255600e30b88cdb6d05430c4044123663e81a9e2b700dd27' or git_blob(raw) != '9e59299a5fe5229a721aa7792678bb4b2e93369c':
        raise ValueError('Pinned publisher catalogue changed')
    catalog = json.loads(raw)
    with urllib.request.urlopen('https://api.github.com/repos/pnlong/jazzsamba-demo/git/trees/' + COMMIT + '?recursive=1', timeout=25) as response:
        tree_packet = json.loads(response.read(2_000_001))
    if tree_packet.get('truncated'):
        raise ValueError('Publisher Git tree is truncated')
    tree = {entry['path']: entry for entry in tree_packet['tree'] if entry['type'] == 'blob'}
    selected = []
    for identifier, split in PICKS:
        song = next(song for song in catalog['songs'] if song['song_id'] == identifier)
        selected.append({'song_id': identifier, 'id': 'jazzsamba-' + song['song_subdir_basename'].replace('_', '-') + '-preferred-first60',
                         'split': split, 'song': song,
                         'audio_git_blob': tree[song['audio_url']], 'annotation_git_blob': tree[song['annotations_url']]})
    selection = {'schema_version': 'bar-chart-selection-1.0', 'frozen_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 'publisher_commit': COMMIT, 'catalog_sha256': pilot.sha(catalog_path), 'cases': selected,
                 'candidates': CANDIDATES, 'conditions': CONDITIONS, 'settings': SETTINGS,
                 'implementation_sha256': pins(), 'clip_policy': 'Exactly first 60.000 seconds from zero; no trimming, gold offset or endpoint scaling',
                 'reference_semantics': 'Written musical chart projected to main triads; independent wallclock bar-grid annotations are scoring targets, not performed note/attack labels',
                 'frozen_before': 'New audio/annotation acquisition, NNLS/pulse inference and model output',
                 'prior_outcomes': 'The exposed earlier three clips motivate this separate prototype; no new input result was consumed for selection/settings'}
    output.mkdir(parents=True)
    save(output / 'selection.json', selection)
    rows = []
    for picked in selected:
        song, identifier = picked['song'], picked['id']
        directory = output / 'cases' / identifier
        directory.mkdir(parents=True)
        ann_raw, ann_pin = fetch(song['annotations_url'], tree, 2_000_000)
        annotation = json.loads(ann_raw)
        (directory / 'source-annotations.json').write_bytes(ann_raw)
        # The complete musical model is built without access to wallclock fields.
        chart = musical_chart(annotation, song, identifier, ann_pin['sha256'])
        chart_paths = {}
        for condition in CONDITIONS:
            relative = f'cases/{identifier}/{condition}-musical.json'
            save(output / relative, condition_chart(chart, condition))
            chart_paths[condition] = {'path': relative, 'sha256': pilot.sha(output / relative)}
        mp3_raw, mp3_pin = fetch(song['audio_url'], tree, 16_000_000)
        mp3 = directory / 'source-preferred.mp3'
        mp3.write_bytes(mp3_raw)
        audio = directory / 'audio.wav'
        subprocess.run(['/opt/homebrew/bin/ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(mp3), '-t', '60.000', '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', str(audio)], check=True)
        with wave.open(str(audio)) as stream:
            if stream.getnchannels() != 1 or stream.getsampwidth() != 2 or stream.getframerate() != 22050 or stream.getnframes() != 1_323_000:
                raise ValueError('Prepared recording is not the fixed 60-second mono PCM16 waveform')
        recording = {'id': identifier, 'title': song['title'] + ' / JazzSAMBA preferred first60', 'sample_rate_hz': 22050,
                     'duration_seconds': 60., 'audio_sha256': pilot.sha(audio)}
        ref = reference(annotation, recording)
        save(directory / 'scoring-reference.json', ref)
        rows.append({'id': identifier, 'split': picked['split'], 'audio': str(audio.relative_to(output)), 'audio_sha256': recording['audio_sha256'],
                     'recording': recording, 'charts': chart_paths, 'reference': str((directory / 'scoring-reference.json').relative_to(output)),
                     'reference_sha256': pilot.sha(directory / 'scoring-reference.json'), 'annotation': ann_pin, 'publisher_mp3': mp3_pin})
        print('Prepared full chart and exact audio:', identifier, len(chart['positions']), 'positions', flush=True)
    protocol = {'schema_version': 'bar-chart-protocol-1.0', 'selection': selection, 'selection_sha256': pilot.sha(output / 'selection.json'),
                'cases': rows, 'accepted_for_playback': False, 'training_exclusion_proven': False,
                'full_source_chart_used': True, 'source_wallclock_values_used_in_inference': False,
                'source_seconds_or_prediction_fit_used_for_origin_selection': False}
    save(output / 'protocol.json', protocol)
    return protocol


def labels_at(chart: dict, coordinates: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows = chart['positions']
    starts = np.array([row['start_quarter_note'] for row in rows])
    ends = np.array([row['end_quarter_note'] for row in rows])
    indices = np.searchsorted(starts, coordinates, side='right') - 1
    valid = (indices >= 0) & (indices < len(rows))
    bounded = np.clip(indices, 0, len(rows) - 1)
    valid &= coordinates < ends[bounded]
    labels = np.array([row['label'] for row in rows], dtype=object)[bounded]
    return np.where(valid, labels, 'X'), np.where(valid, indices, -1)


def score_hypothesis(chart: dict, evidence: dict, coordinates: np.ndarray, covered: np.ndarray | None = None) -> float:
    labels, _ = labels_at(chart, coordinates)
    chroma = np.asarray(evidence['chroma_c_first'])
    active = ~np.asarray(evidence['silent'], dtype=bool)
    if not np.any(active):
        raise ValueError('No active audio evidence for chart alignment')
    scores = np.zeros(len(labels))
    for label in set(labels):
        if label in ('N', 'X'):
            continue
        mask = labels == label
        scores[mask] = np.einsum('ij,j->i', chroma[mask], chart_aligner.chord_template(label))
    if covered is not None:
        scores[~covered] = 0.
    return float(np.mean(scores[active]))


def infer(chart: dict, evidence: dict, candidate: str, pulses: dict | None = None) -> dict:
    validate_chart(chart)
    if chart['recording_id'] != evidence['recording']['id']:
        raise ValueError('Exact evidence/chart recording identity mismatch')
    times = np.array(evidence['times_seconds'])
    meter = chart['quarter_notes_per_bar']
    origins = np.arange(-meter * SETTINGS['origin_bar_radius'], meter * SETTINGS['origin_bar_radius'] + .001, SETTINGS['origin_quarter_note_steps'])
    hypotheses = []
    if candidate == CANDIDATES[0]:
        for factor in SETTINGS['tempo_factors']:
            bpm = chart['declared_bpm'] * factor
            for origin in origins:
                coordinates = times * bpm / 60. + origin
                objective = score_hypothesis(chart, evidence, coordinates)
                hypotheses.append((objective, -abs(factor - 1), -abs(origin), {'tempo_factor': factor, 'bpm': bpm, 'origin_quarter_note_at_audio_zero': float(origin)}))
    elif candidate == CANDIDATES[1]:
        if not pulses or pulses['recording']['audio_sha256'] != evidence['recording']['audio_sha256'] or pulses['recording']['id'] != chart['recording_id']:
            raise ValueError('Audio pulse grid must be exact-paired')
        pulse_times = np.array(pulses['pulse']['beat_times_seconds'])
        pulse_indices = np.arange(len(pulse_times))
        covered = (times >= pulse_times[0]) & (times <= pulse_times[-1])
        coordinates = np.interp(times, pulse_times, pulse_indices)
        for convention in SETTINGS['quarter_notes_per_detected_pulse']:
            for origin in origins:
                objective = score_hypothesis(chart, evidence, coordinates * convention + origin, covered)
                hypotheses.append((objective, -abs(math.log2(convention)), -abs(origin),
                                   {'quarter_notes_per_detected_pulse': convention, 'origin_quarter_note_at_first_detected_pulse': float(origin),
                                    'pulse_bpm': pulses['pulse']['pulse_bpm'], 'quarter_note_bpm': pulses['pulse']['pulse_bpm'] * convention}))
    else:
        raise ValueError('Undeclared candidate')
    best = max(hypotheses, key=lambda row: row[:3])
    parameters = best[3]
    duration = evidence['recording']['duration_seconds']
    if candidate == CANDIDATES[0]:
        transform = lambda x: (x - parameters['origin_quarter_note_at_audio_zero']) * 60. / parameters['bpm']
        lower, upper = 0., duration
    else:
        convention = parameters['quarter_notes_per_detected_pulse']
        origin = parameters['origin_quarter_note_at_first_detected_pulse']
        def transform(x):
            index = (x - origin) / convention
            if index < 0:
                return -math.inf
            if index > len(pulse_times) - 1:
                return math.inf
            return float(np.interp(index, pulse_indices, pulse_times))
        lower, upper = float(pulse_times[0]), float(pulse_times[-1])
    events, visited = [], []
    if lower > 0:
        events.append({'start_seconds': 0., 'end_seconds': lower, 'label': 'X'})
    cursor = lower
    for index, position in enumerate(chart['positions']):
        start, end = max(lower, transform(position['start_quarter_note'])), min(upper, transform(position['end_quarter_note']))
        if end <= start:
            continue
        if start > cursor:
            events.append({'start_seconds': cursor, 'end_seconds': start, 'label': 'X'})
        if events and events[-1]['label'] == position['label'] and abs(events[-1]['end_seconds'] - start) < 1e-8:
            events[-1]['end_seconds'] = end
        else:
            events.append({'start_seconds': start, 'end_seconds': end, 'label': position['label']})
        cursor = end
        visited.append(index)
    if cursor < duration:
        if events and events[-1]['label'] == 'X':
            events[-1]['end_seconds'] = duration
        else:
            events.append({'start_seconds': cursor, 'end_seconds': duration, 'label': 'X'})
    if not events:
        events = [{'start_seconds': 0., 'end_seconds': duration, 'label': 'X'}]
    result = {'schema_version': '1.0', 'recording': evidence['recording'],
              'analysis': {'id': 'bar-chart-' + candidate, 'algorithm': candidate, 'version': '0.1', 'runtime_seconds': 0.,
                           'parameters': {**parameters, 'origin_search': 'Audio-only NNLS acoustic fit; no annotated-time offset fitting', 'quarter_notes_per_bar': meter,
                                          'objective': best[0], 'objective_is_confidence': False, 'hypotheses': len(hypotheses)}},
              'chords': events, 'diagnostics': {'accepted_for_playback': False, 'arrangement_verified': False,
                                             'partial_full_chart_prefix': len(visited) < len(chart['positions']),
                                             'visited_full_chart_positions': visited, 'full_chart_positions': len(chart['positions']),
                                             'unresolved_zero_extent_positions_count': len(chart.get('unresolved_zero_extent_positions', [])),
                                             'unvisited_full_chart_positions': len(chart['positions']) - len(visited),
                                             'unvisited_position_semantics': 'Full written chart beyond the 60-second audio prefix is expected and not forced into the excerpt',
                                             'physical_attack_accuracy': 'not measured'}}
    lab.validate_chart(result)
    return result


def extract_pulse(audio: Path, chart_path: Path, output: Path) -> None:
    chart = json.loads(chart_path.read_text())
    validate_chart(chart)
    signal, rate = lab.read_wav(audio)
    prediction = rhythm_grid.track_audio(audio, {'start_bpm': chart['declared_bpm']})
    rhythm_grid.validate_pulses(prediction, len(signal) / rate)
    save(output, {'schema_version': 'bar-chart-audio-pulses-1.0', 'recording': {'id': chart['recording_id'], 'audio_sha256': pilot.sha(audio),
                                                                           'sample_rate_hz': rate, 'duration_seconds': len(signal) / rate}, 'pulse': prediction})


def run(output: Path) -> dict:
    protocol = json.loads((output / 'protocol.json').read_text())
    selection = protocol['selection']
    if selection['settings'] != SETTINGS or selection['implementation_sha256'] != pins() or pilot.sha(output / 'selection.json') != protocol['selection_sha256']:
        raise ValueError('Frozen selection/settings/implementation changed')
    if (output / 'report.json').exists():
        raise ValueError('Frozen report already exists')
    for case in protocol['cases']:
        if pilot.sha(output / case['audio']) != case['audio_sha256'] or pilot.sha(output / case['reference']) != case['reference_sha256']:
            raise ValueError('Exact audio/reference changed')
        for chart in case['charts'].values():
            if pilot.sha(output / chart['path']) != chart['sha256']:
                raise ValueError('Frozen full musical input changed')
        directory = output / 'cases' / case['id']
        if (directory / 'nnls-evidence.json').exists() or (directory / 'audio-pulses.json').exists() or any((directory / (condition + '-' + candidate + '.json')).exists() for condition in CONDITIONS for candidate in CANDIDATES):
            raise ValueError('Refusing existing inference artifacts')
    rows, evidence_rows = [], []
    for case in protocol['cases']:
        directory = output / 'cases' / case['id']
        audio = output / case['audio']
        evidence = nnls_chroma_adapter.extract(audio, case['id'])
        save(directory / 'nnls-evidence.json', evidence)
        pulse_status = {'status': 'error'}
        try:
            subprocess.run([str(lab.ROOT / '.venv-crema/bin/python'), str(Path(__file__).resolve()), 'extract-pulse', '--audio', str(audio),
                            '--chart', str(output / case['charts'][CONDITIONS[0]]['path']), '--output', str(directory / 'audio-pulses.json')], check=True, timeout=120)
            pulses = json.loads((directory / 'audio-pulses.json').read_text())
            pulse_status = {'status': 'ok', 'sha256': pilot.sha(directory / 'audio-pulses.json'), 'prediction': pulses['pulse']}
        except Exception as error:
            pulses = None
            pulse_status['error'] = type(error).__name__ + ': ' + str(error)
        evidence_rows.append({'id': case['id'], 'nnls_sha256': pilot.sha(directory / 'nnls-evidence.json'), 'extraction_seconds': evidence['analysis']['runtime_seconds'], 'pulses': pulse_status})
        for condition in CONDITIONS:
            chart = json.loads((output / case['charts'][condition]['path']).read_text())
            for candidate in CANDIDATES:
                row = {'id': case['id'], 'split': case['split'], 'condition': condition, 'candidate': candidate, 'status': 'error'}
                try:
                    started = time.perf_counter()
                    prediction = infer(chart, evidence, candidate, pulses)
                    prediction['analysis']['runtime_seconds'] = time.perf_counter() - started
                    relative = 'cases/' + case['id'] + '/' + condition + '-' + candidate + '.json'
                    save(output / relative, prediction)
                    # Only now load the independently saved wallclock target.
                    ref = lab.load_chart(output / case['reference'])
                    row.update(status='ok', prediction=relative, prediction_sha256=pilot.sha(output / relative),
                               semantic=previous.agreement(ref, prediction, candidate), boundary=previous.boundary_score(ref, prediction),
                               model_parameters=prediction['analysis']['parameters'], diagnostics=prediction['diagnostics'])
                except Exception as error:
                    row['error'] = type(error).__name__ + ': ' + str(error)
                rows.append(row)
                print(case['id'], condition, candidate, row['status'], flush=True)
    summary = []
    for condition in CONDITIONS:
        for candidate in CANDIDATES:
            for split in ('all', 'development', 'holdout'):
                requested = [row for row in rows if row['condition'] == condition and row['candidate'] == candidate and (split == 'all' or row['split'] == split)]
                good = [row for row in requested if row['status'] == 'ok']
                result = {'condition': condition, 'candidate': candidate, 'split': split, 'requested': len(requested), 'successful': len(good), 'failed': len(requested) - len(good)}
                for metric in ('root', 'majmin'):
                    eligible = sum(row['semantic'][metric + '_eligible_seconds'] for row in good)
                    result[metric] = sum((row['semantic'][metric] or 0) * row['semantic'][metric + '_eligible_seconds'] for row in good) / eligible if eligible else None
                    result[metric + '_eligible_seconds'] = eligible
                for metric in ('duration_seconds', 'estimated_unknown_seconds', 'retained_harmonic_seconds', 'retained_correct_majmin_seconds', 'retained_wrong_majmin_seconds', 'retained_harmonic_on_unknown_reference_seconds'):
                    result[metric] = sum(row['semantic'][metric] for row in good)
                for metric in ('reference_supported_grid_boundaries', 'predicted_supported_harmonic_boundaries', 'matched_grid_boundaries_150ms'):
                    result[metric] = sum(row['boundary'][metric] for row in good)
                matched, expected, actual = (result[key] for key in ('matched_grid_boundaries_150ms', 'reference_supported_grid_boundaries', 'predicted_supported_harmonic_boundaries'))
                result['grid_boundary_f1_150ms'] = 2 * matched / (expected + actual) if expected + actual else None
                summary.append(result)
    result = {'schema_version': 'bar-chart-alignment-check-1.0', 'date': '2026-10-12', 'protocol': protocol,
              'protocol_sha256': pilot.sha(output / 'protocol.json'), 'evidence': evidence_rows, 'summary': summary, 'cases': rows,
              'accepted_for_playback': False,
              'limitations': ['Main/triad projection with known full written coordinates and BPM/meter is an easier conditional task, not audio-only recognition or playable substitution verification.',
                              'Source wallclock seconds are absent from inference; legitimate audio-only origin/tempo search is explicitly reported, with no gold offset fitting or endpoint scaling.',
                              'Full chart produces a partial audio prefix; no source-time filtering or forced completion of the full arrangement.',
                              'Reported timing targets are publisher written bar-grid boundaries, not independently marked physical harmonic attacks.',
                              'Fresh experiment inputs/settings are frozen before acquisition/inference; pretrained-model training exclusion is unproven.',
                              'Three jazz mixtures cannot establish general rock-song accuracy, correction effort or beginner usefulness.',
                              'Native NNLS acoustic support is about 743ms/hop93ms at 22050Hz; inferred coordinate interpolation adds no acoustic resolution.',
                              'Wrong chart controls remain unaccepted even if their acoustic objective appears competitive; cosine is not calibrated confidence.',
                              'Dataset audio licence unresolved; source music and full annotations remain local and untracked.']}
    save(output / 'report.json', result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'extract-pulse'))
    parser.add_argument('--output', type=Path, default=lab.GENERATED / 'bar-chart-alignment-v1')
    parser.add_argument('--audio', type=Path)
    parser.add_argument('--chart', type=Path)
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.output.resolve())
    elif args.command == 'extract-pulse':
        extract_pulse(args.audio.resolve(), args.chart.resolve(), args.output.resolve())
    else:
        result = run(args.output.resolve())
        print(json.dumps([row for row in result['summary'] if row['split'] == 'all'], indent=2))


if __name__ == '__main__':
    main()
