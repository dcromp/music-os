"""Frozen fresh GuitarSet chord diagnostic; isolated comping and solos, not app accuracy.

Prepare verified local pulse-pack audio and native JAMS references, run unchanged
candidate adapters on an audio-only manifest, and score exact paired predictions.
No downloading, retuning, source separation, key/tempo hints or boundary scoring.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import wave

import numpy as np
import lab
import guitarset_pilot as pilot

ROOT = lab.ROOT
SELECTION = ROOT / 'experiments/fixtures/rhythm-reference-selection.json'
PROTOCOL = ROOT / 'experiments/fixtures/guitarset-validation-protocol.json'
PULSE_PACK = lab.GENERATED / 'guitarset-rhythm-reference-v1'
ANNOTATIONS = ROOT / 'experiments/candidate-assets/guitarset-rhythm-20261012/annotations'
OUTPUT = lab.GENERATED / 'guitarset-chord-validation-v1'
CANDIDATES = ('baseline', 'btc', 'crema', 'chordmini', 'chordino')
PERFORMED_RULE = 'segmentation and root derived from sheet music'
LIMITATIONS = ('Frozen before this new inference; isolated acoustic guitar, four comping and six solo '
               'performances. Development/holdout describes this experiment, not proven exclusion from '
               'model training. Intended labels are lead-sheet harmony; performed labels are sheet-informed '
               'note-derived symbolic transcriptions whose roots and segmentation inherit the lead sheet. '
               'Solo scores measure contextual harmony agreement, not necessarily simultaneous sounding '
               'chords. Unknown X is not silence. Root/major-minor metrics retain eligible-duration '
               'coverage; excluded performed qualities do not earn credit. No physical boundary accuracy, '
               'timing offset fitting, source separation, key guidance or full-mix app accuracy claim.')


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def write_new(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def confined(base: Path, relative: str) -> Path:
    path = (base / relative).resolve(strict=True)
    if not path.is_relative_to(base.resolve()) or Path(relative).is_absolute():
        raise ValueError('Asset path leaves its manifest directory')
    return path


def validate_protocol(protocol_path: Path, selection_path: Path, root: Path = ROOT,
                      *, verify_model_assets: bool = True) -> dict:
    protocol = read(protocol_path)
    if protocol.get('schema_version') != 'guitarset-chord-protocol-1.0':
        raise ValueError('Unsupported frozen protocol')
    if pilot.sha(selection_path) != protocol['selection_sha256']:
        raise ValueError('Frozen selection hash mismatch')
    if protocol['candidates'] != list(CANDIDATES):
        raise ValueError('Frozen candidate settings mismatch')
    for relative, expected in protocol['frozen_files'].items():
        if not verify_model_assets and (relative.startswith('.venv-')
                                       or relative.startswith('experiments/candidate-assets/')):
            continue
        if pilot.sha(confined(root, relative)) != expected:
            raise ValueError('Frozen source/config/model hash mismatch: ' + relative)
    return protocol


def annotation_pair(jams: dict) -> tuple[dict, dict]:
    chords = [a for a in jams['annotations'] if a['namespace'] == 'chord']
    if len(chords) != 2:
        raise ValueError('Expected exactly two native GuitarSet chord annotations')
    performed = [a for a in chords if PERFORMED_RULE in a['annotation_metadata']['annotation_rules']]
    intended = [a for a in chords if not a['annotation_metadata']['annotation_rules']]
    if len(performed) != 1 or len(intended) != 1:
        raise ValueError('Unexpected intended/performed annotation semantics')
    # Sheet-informed symbolic roots and boundaries must not become onset gold.
    if len(intended[0]['data']) != len(performed[0]['data']):
        raise ValueError('Native paired chord interval counts differ')
    for first, second in zip(intended[0]['data'], performed[0]['data']):
        if (first['time'], first['duration']) != (second['time'], second['duration']):
            raise ValueError('Native intended/performed sheet-grid boundaries differ')
        if first['value'] not in ('N', 'X') and second['value'] not in ('N', 'X'):
            if first['value'].split(':')[0] != second['value'].split(':')[0]:
                raise ValueError('Native performed root differs from sheet-derived root')
    return intended[0], performed[0]


def reference_chart(recording: dict, annotation: dict, kind: str) -> dict:
    duration = recording['duration_seconds']
    events = []
    for observation in annotation['data']:
        start, length = float(observation['time']), float(observation['duration'])
        if not math.isfinite(start) or not math.isfinite(length) or start < 0 or length <= 0:
            raise ValueError('Invalid native reference timing')
        if start >= duration:
            continue
        events.append({'start_seconds': start, 'end_seconds': min(duration, start + length),
                       'label': observation['value'], 'native_label': observation['value'],
                       'source_time': start, 'source_duration': length})
    chart = {'schema_version': '1.0', 'recording': dict(recording),
             'analysis': {'id': 'guitarset-' + kind, 'algorithm': 'dataset-reference',
                          'version': '1.1.0', 'runtime_seconds': 0,
                          'parameters': {'reference_kind': kind, 'annotation_namespace': 'chord',
                                         'metadata': annotation['annotation_metadata'],
                                         'boundaries': 'Native sheet-derived grid; not played-onset gold'}},
             'chords': events}
    lab.validate_chart(chart)
    pilot.complete_intervals(events, duration, lambda event: pilot.to_harte(event['native_label'], True))
    return chart


def verify_recording(recording: dict, audio: Path) -> None:
    with wave.open(str(audio)) as stream:
        rate, count = stream.getframerate(), stream.getnframes()
        if stream.getnchannels() != 1 or stream.getsampwidth() != 2:
            raise ValueError('Prepared audio must remain mono PCM16')
    if (recording.get('audio_sha256') != pilot.sha(audio)
            or recording.get('sample_rate_hz') != rate
            or abs(recording.get('duration_seconds', -1) - count / rate) > 1e-9):
        raise ValueError('Exact audio hash/rate/duration pairing mismatch')


def prepare(selection_path: Path, pulse_pack: Path, annotations: Path, output: Path,
            protocol_path: Path = PROTOCOL) -> dict:
    protocol = validate_protocol(protocol_path, selection_path)
    selection, pulse_manifest = read(selection_path), read(pulse_pack / 'manifest.json')
    if pulse_manifest.get('selection_sha256') != protocol['selection_sha256']:
        raise ValueError('Pulse input selection hash mismatch')
    chosen = selection['cases']
    if len(chosen) != 10 or len({c['id'] for c in chosen}) != 10:
        raise ValueError('Fresh diagnostic requires the exact frozen ten distinct cases')
    pulse_cases = pulse_manifest['cases']
    if (len(pulse_cases) != len(chosen)
            or {c['id'] for c in pulse_cases} != {c['id'] for c in chosen}):
        raise ValueError('Pulse manifest case set differs from frozen selection')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output already contains assets; refusing to overwrite prepared evidence')
    # Validate every input and both reference kinds before writing any outputs.
    ready = []
    for case in chosen:
        source_folder = confined(pulse_pack, 'cases/' + case['id'])
        source = read(source_folder / 'source.json')
        audio = source_folder / 'audio.wav'
        pulse_case = next(c for c in pulse_cases if c['id'] == case['id'])
        recording = pulse_case['recording']
        if recording['id'] != case['id']:
            raise ValueError('Pulse recording ID mismatch')
        verify_recording(recording, audio)
        native = annotations / (case['original_id'] + '.jams')
        if (source['original_id'] != case['original_id']
                or source['selection_sha256'] != protocol['selection_sha256']
                or source['prepared_audio_sha256'] != recording['audio_sha256']
                or pilot.sha(native) != case['source_jams_sha256']
                or source['source_jams_sha256'] != case['source_jams_sha256']):
            raise ValueError('Source/JAMS provenance hash mismatch')
        if source.get('time_origin_seconds') != 0:
            raise ValueError('Prepared source time origin must remain zero')
        if case['split'] not in ('development', 'holdout'):
            raise ValueError('Unsupported frozen split')
        task = case['original_id'].rsplit('_', 1)[1]
        if task not in ('comp', 'solo'):
            raise ValueError('Unknown performance task')
        pair = annotation_pair(read(native))
        references = {kind: reference_chart(recording, annotation, kind)
                      for kind, annotation in zip(('intended', 'performed'), pair)}
        ready.append((case, task, audio, source, recording, references))
    output.mkdir(parents=True, exist_ok=True)
    cases, audio_cases = [], []
    for case, task, audio, source, recording, references in ready:
        folder = output / 'cases' / case['id']
        folder.mkdir(parents=True)
        shutil.copyfile(audio, folder / 'audio.wav')
        write_new(folder / 'source.json', source)
        for kind, reference in references.items():
            write_new(folder / (kind + '.json'), reference)
        metadata = {'id': case['id'], 'original_id': case['original_id'],
                    'split': case['split'], 'performance_type': task,
                    'recording': recording, 'audio': 'cases/' + case['id'] + '/audio.wav',
                    'source_sha256': pilot.sha(folder / 'source.json')}
        for kind in references:
            metadata[kind + '_reference'] = 'cases/' + case['id'] + '/' + kind + '.json'
            metadata[kind + '_reference_sha256'] = pilot.sha(folder / (kind + '.json'))
        cases.append(metadata)
        # Candidate processes receive only ID and audio, no labels, tempo, roots or split.
        audio_cases.append({'id': case['id'], 'audio': metadata['audio']})
    write_new(output / 'audio-manifest.json', {'schema_version': 'audio-only-candidate-inputs-1.0', 'cases': audio_cases})
    manifest = {'schema_version': 'guitarset-chord-validation-1.0',
                'selection_sha256': protocol['selection_sha256'],
                'protocol_sha256': pilot.sha(protocol_path), 'protocol': protocol,
                'pulse_input_manifest_sha256': pilot.sha(pulse_pack / 'manifest.json'),
                'audio_manifest_sha256': pilot.sha(output / 'audio-manifest.json'),
                'cases': cases, 'limitations': LIMITATIONS}
    write_new(output / 'manifest.json', manifest)
    return manifest


def validate_prepared(output: Path, protocol_path: Path = PROTOCOL,
                      *, verify_model_assets: bool = True) -> dict:
    manifest = read(output / 'manifest.json')
    protocol = validate_protocol(protocol_path, SELECTION, verify_model_assets=verify_model_assets)
    if (manifest['protocol_sha256'] != pilot.sha(protocol_path)
            or manifest['protocol'] != protocol
            or manifest['selection_sha256'] != protocol['selection_sha256']
            or manifest['audio_manifest_sha256'] != pilot.sha(output / 'audio-manifest.json')):
        raise ValueError('Prepared manifest/protocol/audio-manifest changed')
    audio_manifest = read(output / 'audio-manifest.json')
    expected = [{'id': c['id'], 'audio': c['audio']} for c in manifest['cases']]
    if audio_manifest['cases'] != expected:
        raise ValueError('Audio-only manifest exact case pairing mismatch')
    selection = read(SELECTION)
    if (len(manifest['cases']) != len(selection['cases'])
            or [c['id'] for c in manifest['cases']] != [c['id'] for c in selection['cases']]):
        raise ValueError('Prepared cases differ from frozen selection')
    for case, frozen in zip(manifest['cases'], selection['cases']):
        if (case['original_id'] != frozen['original_id'] or case['split'] != frozen['split']
                or case['performance_type'] != frozen['original_id'].rsplit('_', 1)[1]):
            raise ValueError('Prepared split/task differs from frozen selection')
        verify_recording(case['recording'], confined(output, case['audio']))
        source_path = confined(output, 'cases/' + case['id'] + '/source.json')
        if pilot.sha(source_path) != case['source_sha256']:
            raise ValueError('Prepared source provenance hash mismatch')
        for kind in ('intended', 'performed'):
            if pilot.sha(confined(output, case[kind + '_reference'])) != case[kind + '_reference_sha256']:
                raise ValueError('Reference hash mismatch; refusing altered reference')
    return manifest


def checked_score(reference: dict, prediction: dict, candidate: str) -> dict:
    # Original pilot scorer supplies native label conversion and root/quality metrics.
    for key in ('id', 'audio_sha256', 'sample_rate_hz', 'duration_seconds'):
        if reference['recording'].get(key) != prediction['recording'].get(key):
            raise ValueError('Prediction/reference exact recording pairing mismatch: ' + key)
    return pilot.score(reference, prediction, candidate)


def summarize(rows: list[dict], candidates: list[str], cases: list[dict]) -> list[dict]:
    summaries = []
    for split in ('all', 'development', 'holdout'):
        for task in ('all', 'comp', 'solo'):
            requested = [c for c in cases if (split == 'all' or c['split'] == split)
                         and (task == 'all' or c['performance_type'] == task)]
            if not requested:
                continue
            for kind in ('intended', 'performed'):
                for candidate in candidates:
                    group = [r for r in rows if r['reference_kind'] == kind and r['candidate'] == candidate
                             and (split == 'all' or r['split'] == split)
                             and (task == 'all' or r['performance_type'] == task)]
                    good = [r for r in group if r['status'] == 'ok']
                    total = sum(r['duration_seconds'] for r in good)
                    requested_duration = sum(c['recording']['duration_seconds'] for c in requested)
                    result = {'split': split, 'performance_type': task, 'reference_kind': kind,
                              'candidate': candidate, 'requested_cases': len(requested),
                              'successful_cases': len(good), 'failed_cases': len(requested) - len(good),
                              'requested_audio_seconds': requested_duration, 'scored_audio_seconds': total,
                              'scored_audio_coverage': total / requested_duration if requested_duration else None}
                    for metric in ('root', 'majmin', 'root_chord_only', 'majmin_chord_only'):
                        eligible = sum(r[metric + '_eligible_seconds'] for r in good)
                        result[metric] = (sum((r[metric] or 0) * r[metric + '_eligible_seconds'] for r in good)
                                          / eligible if eligible else None)
                        result[metric + '_eligible_seconds'] = eligible
                        result[metric + '_reference_coverage'] = eligible / total if total else None
                    result['inference_seconds'] = sum(r['analysis_runtime_seconds'] for r in good)
                    result['estimated_unknown_seconds'] = sum(r['estimated_unknown_seconds'] for r in good)
                    summaries.append(result)
    return summaries


def score_output(output: Path, candidates: list[str]) -> dict:
    import mir_eval
    manifest = validate_prepared(output, verify_model_assets=False)
    rows = []
    for candidate in candidates:
        for case in manifest['cases']:
            prediction_path = output / 'cases' / case['id'] / (candidate + '.json')
            for kind in ('intended', 'performed'):
                row = {key: case[key] for key in ('id', 'original_id', 'split', 'performance_type')}
                row.update(candidate=candidate, reference_kind=kind, status='ok')
                try:
                    prediction = lab.load_chart(prediction_path)
                    reference = lab.load_chart(output / case[kind + '_reference'])
                    if reference['recording'] != case['recording']:
                        raise ValueError('Reference recording metadata differs from prepared manifest')
                    row.update(checked_score(reference, prediction, candidate))
                    row['prediction_sha256'] = pilot.sha(prediction_path)
                    row['analysis_provenance'] = prediction['analysis']
                except Exception as exc:
                    row.update(status='error', error=type(exc).__name__ + ': ' + str(exc))
                rows.append(row)
    attempt_records = [{'path': str(path.relative_to(output)), 'sha256': pilot.sha(path)}
                       for path in sorted((output / 'attempts').rglob('*')) if path.is_file()]
    batch_summaries = [{'path': str(path.relative_to(output)), 'value': read(path)}
                       for path in sorted((output / 'attempts').rglob('attempt.json'))]
    report = {'schema_version': 'guitarset-chord-validation-report-1.0',
              'manifest_sha256': pilot.sha(output / 'manifest.json'),
              'protocol_sha256': manifest['protocol_sha256'], 'selection_sha256': manifest['selection_sha256'],
              'evaluator_sha256': pilot.sha(Path(__file__)), 'candidate_requests': candidates,
              'environment': {'python': sys.version, 'numpy': np.__version__, 'mir_eval': mir_eval.__version__},
              'summary': summarize(rows, candidates, manifest['cases']), 'cases': rows,
              'preserved_attempts': attempt_records, 'batch_attempts': batch_summaries,
              'limitations': LIMITATIONS}
    report_path = output / 'report.json'
    if report_path.exists():
        archive = output / 'report-history' / str(time.time_ns())
        archive.mkdir(parents=True)
        shutil.copyfile(report_path, archive / 'report.json')
        if (output / 'report.csv').exists():
            shutil.copyfile(output / 'report.csv', archive / 'report.csv')
    pilot.write(report_path, report)
    columns = sorted({key for row in rows for key in row if key not in ('analysis_provenance', 'prediction_label_conversion')})
    with (output / 'report.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, extrasaction='ignore', lineterminator='\n')
        writer.writeheader(); writer.writerows(rows)
    return report


def run(output: Path, candidates: list[str], reuse: bool = False) -> dict:
    manifest = validate_prepared(output, verify_model_assets=not reuse)
    if not reuse:
        for candidate in candidates:
            # Existing predictions are immutable; explicit --reuse-existing scores them.
            if any((output / 'cases' / c['id'] / (candidate + '.json')).exists() for c in manifest['cases']):
                raise ValueError('Candidate predictions already exist; use --reuse-existing: ' + candidate)
        for candidate in candidates:
            attempt = output / 'attempts' / candidate / str(time.time_ns())
            attempt.mkdir(parents=True)
            started = time.perf_counter()
            if candidate == 'baseline':
                results = []
                for case in manifest['cases']:
                    try:
                        audio = output / case['audio']
                        prediction = lab.detect(audio, case['id'])
                        prediction['recording']['audio_sha256'] = pilot.sha(audio)
                        lab.validate_chart(prediction)
                        write_new(attempt / 'cases' / case['id'] / 'baseline.json', prediction)
                        results.append({'id': case['id'], 'status': 'ok'})
                    except Exception as exc:
                        results.append({'id': case['id'], 'status': 'error', 'error': repr(exc)})
                batch = {'results': results}
            else:
                interpreter = (ROOT / ('.venv-' + candidate) / 'bin/python'
                               if candidate in ('btc', 'crema', 'chordmini') else Path(sys.executable))
                command = [str(interpreter), str(ROOT / 'experiments/analysis/candidates' / (candidate + '_adapter.py')),
                           '--batch-manifest', str(output / 'audio-manifest.json'), '--output-root', str(attempt)]
                print('Running frozen fresh batch: ' + candidate, flush=True)
                try:
                    process = subprocess.run(command, capture_output=True, text=True, timeout=600)
                    (attempt / 'batch.log').write_text(process.stdout + process.stderr)
                    batch = {'command': command, 'returncode': process.returncode}
                except (OSError, subprocess.TimeoutExpired) as exc:
                    (attempt / 'batch.log').write_text(str(exc))
                    batch = {'command': command, 'error': repr(exc)}
            batch.update(candidate=candidate, wall_seconds=time.perf_counter() - started,
                         protocol_sha256=manifest['protocol_sha256'])
            write_new(attempt / 'attempt.json', batch)
            for case in manifest['cases']:
                path = attempt / 'cases' / case['id'] / (candidate + '.json')
                if path.exists():
                    # Retain failed attempt originals even if a malformed output cannot score.
                    shutil.copyfile(path, output / 'cases' / case['id'] / (candidate + '.json'))
    return score_output(output, candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'score'))
    parser.add_argument('--selection', type=Path, default=SELECTION)
    parser.add_argument('--pulse-pack', type=Path, default=PULSE_PACK)
    parser.add_argument('--annotations', type=Path, default=ANNOTATIONS)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--candidates', default=','.join(CANDIDATES))
    parser.add_argument('--reuse-existing', action='store_true')
    args = parser.parse_args()
    candidates = args.candidates.split(',')
    if not candidates or len(set(candidates)) != len(candidates) or any(c not in CANDIDATES for c in candidates):
        parser.error('Provide distinct frozen candidate names')
    if args.command == 'prepare':
        manifest = prepare(args.selection.resolve(), args.pulse_pack.resolve(), args.annotations.resolve(), args.output_dir.resolve())
        print('Prepared ' + str(len(manifest['cases'])) + ' exact paired fresh chord inputs')
    else:
        report = (score_output(args.output_dir.resolve(), candidates) if args.command == 'score'
                  else run(args.output_dir.resolve(), candidates, args.reuse_existing))
        print(json.dumps([row for row in report['summary'] if row['split'] == 'all'], indent=2))
        if any(row['status'] != 'ok' for row in report['cases']):
            raise SystemExit(2)


if __name__ == '__main__':
    main()
