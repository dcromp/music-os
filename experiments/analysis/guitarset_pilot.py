"""Six preselected GuitarSet performances: raw-model diagnostic, not an app accuracy claim."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time
import wave

import numpy as np
import lab

ASSETS = lab.ROOT / 'experiments/candidate-assets/guitarset'
OUTPUT = lab.GENERATED / 'guitarset-pilot'
SELECTED = ['00_SS3-84-Bb_comp', '01_Rock1-90-C#_comp', '02_Funk1-97-C_comp',
            '03_BN1-129-Eb_comp', '04_Rock2-142-D_comp', '05_Jazz3-150-C_comp']
EXPECTED_AUDIO_HASHES = [
 'ece4c3e67d8ab31ca6665ef8cd143a61aedeeb6145e45fa4b74120630024039b',
 '2dc712e3457bcde208ae59bf8fab8d7f0d7335368271dd211856a13323b50bee',
 '297b0e0cda8e9e7018801b6adba68f19cfeccd5df48377285a204411648a4f81',
 '8fef5aa0807d145e57c5a4befdc729cf3f185cfcc41c64fee7ead7cb1876b629',
 '77589eeda2dfd7a8e8652b9b0c8a002529d911786e4be29c7bafda31fa32ba99',
 '665e9a0968ec0d81e8cab504d39a4ffbf4249099cf87700c122607be000f508c']
EXPECTED_JAMS_HASHES = [
 'b410e8d7d6ed3040f3674b709c5144267f540a84fab47edc28365891832dcdb5',
 '75a1055d5c9b9a1a59af0296660ce23b1556d72114bbb52717a9564a07a23c96',
 '292c8330635f53e35587e796c76ea47358647474471dfaeb8869167ff34a2549',
 'f41001c65b9b3b62187ed3aace924d01773ec41afe8aceab878af72e0009ece0',
 'aaab63931089e7910af048ab49e10f99c2302b83cdfc78d077e74d5c228625ce',
 '8b914d6bd9b6400791307188689fec33c81ab77b628933d118ce7d899975fb08']
SUFFIXES = {'': 'maj', 'maj': 'maj', 'm': 'min', 'min': 'min', '7': '7', 'maj7': 'maj7',
 'm7': 'min7', 'mmaj7': 'minmaj7', 'm6': 'min6', '6': 'maj6', 'maj6': 'maj6',
 'dim': 'dim', 'dim7': 'dim7', 'm7b5': 'hdim7', 'hdim7': 'hdim7', 'aug': 'aug',
 'sus2': 'sus2', 'sus4': 'sus4', '9': '9', 'maj9': 'maj9', 'm9': 'min9',
 '11': '11', 'm11': 'min11', '13': '13', 'm13': 'min13', '5': '(1,5)'}
DEGREES = ['1', 'b2', '2', 'b3', '3', '4', 'b5', '5', 'b6', '6', 'b7', '7']


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def to_harte(label: str, native_harte: bool = False) -> str:
    """Native Harte basses are relative degrees; display basses are absolute pitches."""
    import mir_eval
    if label in ('N', 'X'):
        return label
    if native_harte or ':' in label:
        mir_eval.chord.encode(label, False)
        return label
    match = re.fullmatch(r'([A-G](?:#|b)*)([^/]*)(?:/([A-G](?:#|b)*))?', label)
    if not match or match[2] not in SUFFIXES:
        raise ValueError(f'Unsupported display label; no guessed conversion: {label!r}')
    root, quality, bass = match.groups()
    result = root + ':' + SUFFIXES[quality]
    if bass:
        relative = (mir_eval.chord.pitch_class_to_semitone(bass)
                    - mir_eval.chord.pitch_class_to_semitone(root)) % 12
        result += '/' + DEGREES[relative]
    mir_eval.chord.encode(result, False)
    return result


def prediction_label(event: dict, candidate: str) -> str:
    if candidate == 'crema':
        if 'native_label' not in event:
            raise ValueError('CREMA requires preserved native Harte label')
        return to_harte(event['native_label'], native_harte=True)
    if candidate == 'chordmini':
        # Checkpoint labels mix implicit-major roots and explicit Harte qualities.
        return to_harte(event.get('native_label', event['label']))
    # Chordino's host uses display syntax and absolute bass notes, per built-in dictionary.
    # Its synthetic prefix X explicitly represents an uncovered host interval.
    return to_harte(event['label'])


def complete_intervals(events: list[dict], duration: float, label_fn) -> tuple[np.ndarray, list[str]]:
    """Uncovered intervals are unknown X; never manufacture no-chord N."""
    intervals, labels, previous = [], [], 0.0
    for event in events:
        start, end = max(0.0, float(event['start_seconds'])), min(duration, float(event['end_seconds']))
        if start < previous - 1e-8 or end <= start:
            raise ValueError('Invalid/overlapping reference or prediction intervals')
        if start > previous:
            intervals.append([previous, start]); labels.append('X')
        intervals.append([start, end]); labels.append(label_fn(event)); previous = end
    if previous < duration:
        intervals.append([previous, duration]); labels.append('X')
    if not intervals:
        raise ValueError('Empty timeline')
    return np.asarray(intervals), labels


def score(reference: dict, prediction: dict, candidate: str) -> dict:
    import mir_eval
    lab.validate_chart(reference); lab.validate_chart(prediction)
    duration = reference['recording']['duration_seconds']
    if reference['recording']['id'] != prediction['recording']['id']:
        raise ValueError('Recording ID mismatch')
    if abs(duration - prediction['recording']['duration_seconds']) > 1 / 22050:
        raise ValueError('Recording duration mismatch')
    ref_int, refs = complete_intervals(reference['chords'], duration, lambda e: to_harte(e['native_label'], True))
    est_int, ests = complete_intervals(prediction['chords'], duration, lambda e: prediction_label(e, candidate))
    intervals, merged_refs, merged_ests = mir_eval.util.merge_labeled_intervals(ref_int, refs, est_int, ests)
    durations = mir_eval.util.intervals_to_durations(intervals)
    ref_roots, _, _ = mir_eval.chord.encode_many(merged_refs, False)
    harmonic = ref_roots >= 0  # Independent reporting prevents silence-credit inflation.
    result = {'duration_seconds': duration,
              'reference_chord_seconds': float(durations[harmonic].sum()),
              'reference_chord_coverage': float(durations[harmonic].sum() / duration)}
    for name, metric in [('root', mir_eval.chord.root), ('majmin', mir_eval.chord.majmin)]:
        comparisons = metric(merged_refs, merged_ests)
        # X is unknown, including any missing detector intervals. It never earns N credit.
        comparisons[(np.asarray(merged_ests) == 'X') & (comparisons >= 0)] = 0
        for suffix, mask in [('', comparisons >= 0), ('_chord_only', (comparisons >= 0) & harmonic)]:
            eligible = float(durations[mask].sum())
            correct = float((comparisons[mask] * durations[mask]).sum())
            result[name + suffix] = correct / eligible if eligible else None
            result[name + suffix + '_eligible_seconds'] = eligible
            result[name + suffix + '_reference_coverage'] = eligible / duration
    result['estimated_unknown_seconds'] = float(durations[np.asarray(merged_ests) == 'X'].sum())
    result['estimated_no_chord_seconds_on_reference_chords'] = float(durations[harmonic & (np.asarray(merged_ests) == 'N')].sum())
    result['predicted_events'] = len(prediction['chords'])
    result['analysis_runtime_seconds'] = prediction['analysis']['runtime_seconds']
    result['prediction_label_conversion'] = sorted({(e.get('native_label', e['label']), prediction_label(e, candidate)) for e in prediction['chords']})
    return result


def prepare(assets: Path, output: Path) -> dict:
    """Convert source rate only; preserve all source time and annotations without offsets."""
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for selected, expected_audio, expected_jams in zip(SELECTED, EXPECTED_AUDIO_HASHES, EXPECTED_JAMS_HASHES):
        source_audio, source_jams = assets / 'audio' / (selected + '_mic.wav'), assets / 'annotations' / (selected + '.jams')
        if sha(source_audio) != expected_audio or sha(source_jams) != expected_jams:
            raise ValueError(f'Official asset differs from verified pilot input: {selected}')
        case_id = 'guitarset-' + selected.lower().replace('#', 'sharp').replace('_', '-')
        folder = output / 'cases' / case_id
        folder.mkdir(parents=True, exist_ok=True)
        audio = folder / 'audio.wav'
        if audio.exists():
            provenance_path = folder / 'source.json'
            if not provenance_path.exists():
                raise ValueError('Prepared audio has no source.json; refusing an unverified orphan')
            previous = json.loads(provenance_path.read_text())
            if previous['prepared_audio_sha256'] != sha(audio):
                raise ValueError('Prepared audio changed; refusing to silently reuse it')
            if previous['source_audio_sha256'] != expected_audio or previous['source_jams_sha256'] != expected_jams:
                raise ValueError('Prepared audio provenance differs from selected verified sources')
        else:
            subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(source_audio),
                            '-ac', '1', '-ar', '22050', '-c:a', 'pcm_s16le', str(audio)], check=True)
        signal, sr = lab.read_wav(audio)
        if sr != 22050:
            raise ValueError('Prepared audio has wrong sample rate')
        with wave.open(str(audio)) as wav:
            if wav.getnchannels() != 1:
                raise ValueError('Prepared audio must be mono')
        duration = len(signal) / sr
        jams = json.loads(source_jams.read_text())
        chords = [a for a in jams['annotations'] if a['namespace'] == 'chord']
        if len(chords) != 2 or 'segmentation and root derived from sheet music' not in chords[1]['annotation_metadata']['annotation_rules']:
            raise ValueError('Unexpected GuitarSet chord annotation semantics/order')
        recording = {'id': case_id, 'title': selected + ' / microphone comping', 'duration_seconds': duration,
                     'sample_rate_hz': sr, 'audio_sha256': sha(audio)}
        for kind, annotation in zip(['intended', 'performed'], chords):
            events = [{'start_seconds': max(0.0, obs['time']), 'end_seconds': min(duration, obs['time'] + obs['duration']),
                       'label': obs['value'], 'native_label': obs['value'], 'source_time': obs['time'],
                       'source_duration': obs['duration']} for obs in annotation['data'] if obs['time'] < duration]
            reference = {'schema_version': '1.0', 'recording': recording,
                         'analysis': {'id': 'guitarset-' + kind, 'algorithm': 'dataset-reference', 'version': '1.1.0',
                                      'runtime_seconds': 0, 'parameters': {'annotation_namespace': 'chord',
                                       'reference_kind': kind, 'metadata': annotation['annotation_metadata'],
                                       'boundaries': 'Lead-sheet grid; not physical played-onset gold'}}, 'chords': events}
            lab.validate_chart(reference)
            complete_intervals(events, duration, lambda e: to_harte(e['native_label'], True))
            write(folder / (kind + '.json'), reference)
        source = {'original_id': selected, 'source_audio_sha256': expected_audio, 'source_jams_sha256': expected_jams,
                  'prepared_audio_sha256': sha(audio), 'prepared_duration_seconds': duration,
                  'source_audio': str(source_audio.relative_to(lab.ROOT)) if source_audio.is_relative_to(lab.ROOT) else source_audio.name,
                  'source_jams': str(source_jams.relative_to(lab.ROOT)) if source_jams.is_relative_to(lab.ROOT) else source_jams.name,
                  'preparation': 'FFmpeg mono 22050Hz PCM16; no trimming, padding, gain changes or offset guessing',
                  'ffmpeg_version': subprocess.check_output(['ffmpeg', '-version'], text=True).splitlines()[0],
                  'source_jams_file_metadata': jams['file_metadata'],
                  'dataset_doi': '10.5281/zenodo.3371780', 'dataset_version': '1.1.0', 'dataset_license': 'CC BY 4.0'}
        write(folder / 'source.json', source)
        cases.append({'id': case_id, 'original_id': selected, 'audio': str(audio.relative_to(output)),
                      'reference': str((folder / 'intended.json').relative_to(output)),
                      'performed_reference': str((folder / 'performed.json').relative_to(output)),
                      'intended_reference_sha256': sha(folder / 'intended.json'),
                      'performed_reference_sha256': sha(folder / 'performed.json'), 'source': source})
    manifest = {'pilot_version': '1.0', 'selection': 'Six preselected performances, all six performers and five styles; known-error files excluded; selection preceded inference',
                'cases': cases, 'source': {'record_url': 'https://zenodo.org/records/3371780',
                'audio_url': 'https://zenodo.org/api/records/3371780/files/audio_mono-mic.zip/content',
                'annotation_url': 'https://zenodo.org/api/records/3371780/files/annotation.zip/content',
                'annotation_md5': 'b39b78e63d3446f2e54ddb7a54df9b10',
                'annotation_sha256': '8daa02e6417ccca1685feb44b135e95928ad7037e5032ecb326b5791856fda99',
                'audio_archive_declared_md5': '275966d6610ac34999b58426beb119c3',
                'audio_verification': 'Selected entries only: ZIP CRC32 and SHA256. Full audio archive not downloaded/hash-verified.'}}
    write(output / 'manifest.json', manifest)
    return manifest


def run(output: Path, candidates: list[str], reuse: bool = False) -> dict:
    import mir_eval
    manifest_path = output / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    commands = {c: [lab.ROOT / ('.venv-' + c) / 'bin/python', Path(__file__).parent / 'candidates' / (c + '_adapter.py')]
                for c in ['btc', 'crema', 'chordmini']}
    commands['chordino'] = [Path(sys.executable), Path(__file__).parent / 'candidates/chordino_adapter.py']
    if len(set(candidates)) != len(candidates) or any(c not in {'baseline', *commands} for c in candidates):
        raise ValueError('Candidate list is invalid or duplicated')
    batch_runs, rows = {}, []
    if not reuse and (output / 'report.json').exists():
        archive = output / 'attempts' / str(time.time_ns())
        archive.mkdir(parents=True)
        for path in [output / 'report.json', *output.glob('*-batch.log')]:
            (archive / path.name).write_bytes(path.read_bytes())
    for candidate in candidates:
        if not reuse:
            for case in manifest['cases']:
                (output / 'cases' / case['id'] / (candidate + '.json')).unlink(missing_ok=True)
            started = time.perf_counter()
            if candidate == 'baseline':
                failures = []
                for case in manifest['cases']:
                    try:
                        path = output / case['audio']
                        prediction = lab.detect(path, case['id'])
                        prediction['recording']['audio_sha256'] = sha(path)
                        lab.validate_chart(prediction)
                        write(output / 'cases' / case['id'] / 'baseline.json', prediction)
                    except Exception as exc:
                        failures.append({'id': case['id'], 'error': str(exc)})
                batch_runs[candidate] = {'failures': failures, 'wall_seconds': time.perf_counter() - started}
            else:
                print('Running sequential pilot batch: ' + candidate, flush=True)
                try:
                    proc = subprocess.run([str(v) for v in commands[candidate]] + ['--batch-manifest', str(manifest_path), '--output-root', str(output)],
                                          capture_output=True, text=True, timeout=600)
                    (output / (candidate + '-batch.log')).write_text(proc.stdout + proc.stderr)
                    batch_runs[candidate] = {'returncode': proc.returncode, 'wall_seconds': time.perf_counter() - started}
                except (OSError, subprocess.TimeoutExpired) as exc:
                    batch_runs[candidate] = {'error': str(exc), 'wall_seconds': time.perf_counter() - started}
        for case in manifest['cases']:
            audio = output / case['audio']
            path = output / 'cases' / case['id'] / (candidate + '.json')
            for kind, ref_path in [('intended', case['reference']), ('performed', case['performed_reference'])]:
                row = {'case_id': case['id'], 'original_id': case['original_id'], 'candidate': candidate, 'reference_kind': kind, 'status': 'ok'}
                try:
                    prediction = lab.load_chart(path)
                    if sha(audio) != case['source']['prepared_audio_sha256'] or prediction['recording'].get('audio_sha256') != sha(audio):
                        raise ValueError('Prediction/prepared source hash mismatch')
                    if sha(output / ref_path) != case[kind + '_reference_sha256']:
                        raise ValueError('Reference hash mismatch; refusing to score an altered reference')
                    row.update(score(lab.load_chart(output / ref_path), prediction, candidate))
                    row['prediction_sha256'] = sha(path)
                except Exception as exc:
                    row.update(status='error', error=type(exc).__name__ + ': ' + str(exc))
                rows.append(row)
    summaries = []
    for kind in ['intended', 'performed']:
        for candidate in candidates:
            group = [r for r in rows if r['reference_kind'] == kind and r['candidate'] == candidate]
            good = [r for r in group if r['status'] == 'ok']
            summary = {'candidate': candidate, 'reference_kind': kind, 'successful_cases': len(good), 'failed_cases': len(group) - len(good)}
            for metric in ['root', 'majmin', 'root_chord_only', 'majmin_chord_only']:
                eligible = sum(r[metric + '_eligible_seconds'] for r in good)
                total = sum(r['duration_seconds'] for r in good)
                summary[metric] = sum((r[metric] or 0) * r[metric + '_eligible_seconds'] for r in good) / eligible if eligible else None
                summary[metric + '_reference_coverage'] = eligible / total if total else None
                summary[metric + '_eligible_seconds'] = eligible
            summary['inference_seconds'] = sum(r['analysis_runtime_seconds'] for r in good)
            summary['estimated_no_chord_seconds_on_reference_chords'] = sum(r['estimated_no_chord_seconds_on_reference_chords'] for r in good)
            summaries.append(summary)
    batch_summaries = {}
    for candidate in candidates:
        path = output / (candidate + '-batch-summary.json')
        if path.exists():
            batch_summaries[candidate] = json.loads(path.read_text())
    attempts = [{'path': str(path.relative_to(output)), 'sha256': sha(path)}
                for path in sorted((output / 'attempts').rglob('*')) if path.is_file()]
    runtime_attempt_failures = []
    for path in sorted((output / 'attempts').rglob('*report.json')):
        archived = json.loads(path.read_text())
        for candidate, batch in archived.get('batch_runs', {}).items():
            if batch.get('returncode', 0) == 0 and 'error' not in batch:
                continue
            logs = list(path.parent.glob('*' + candidate + '-batch.log'))
            diagnostic = logs[0].read_text()[:1000] if logs else batch.get('error', '')
            runtime_attempt_failures.append({'candidate': candidate, 'returncode': batch.get('returncode'),
                'stage': 'before inference: OpenMP startup' if 'OMP:' in diagnostic and 'SHM' in diagnostic else 'runtime',
                'diagnostic': diagnostic, 'accuracy_score': None, 'archived_report': str(path.relative_to(output))})
    report = {'pilot_version': '1.0', 'dataset': manifest, 'candidate_requests': candidates, 'reused_predictions': reuse,
              'environment': {'python': sys.version, 'numpy': np.__version__, 'mir_eval': mir_eval.__version__},
              'batch_runs': batch_runs, 'candidate_batch_summaries': batch_summaries, 'preserved_attempts': attempts,
              'runtime_attempt_failures': runtime_attempt_failures,
              'summary': summaries, 'cases': rows,
              'limitations': 'Six preselected microphone acoustic-guitar comping performances; raw model diagnostic, not app accuracy or independent-training-overlap proof. Lead-sheet-derived roots/boundaries. No boundary metric, source separation, key hints, tuning or founder ratings.'}
    write(output / 'report.json', report)
    columns = sorted({k for row in rows for k in row if k != 'prediction_label_conversion'})
    with (output / 'report.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator='\n', extrasaction='ignore'); writer.writeheader(); writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'run'])
    parser.add_argument('--assets', type=Path, default=ASSETS)
    parser.add_argument('--output-dir', type=Path, default=OUTPUT)
    parser.add_argument('--candidates', default='baseline,btc,crema,chordmini,chordino')
    parser.add_argument('--reuse-existing', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        manifest = prepare(args.assets.resolve(), args.output_dir.resolve())
        print('Prepared ' + str(len(manifest['cases'])) + ' verified performances')
    else:
        report = run(args.output_dir.resolve(), args.candidates.split(','), args.reuse_existing)
        print(json.dumps(report['summary'], indent=2))
        if any(row['status'] != 'ok' for row in report['cases']):
            raise SystemExit(2)

if __name__ == '__main__':
    main()
