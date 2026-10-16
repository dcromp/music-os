"""Frozen conditional chart alignment on publisher-paired JazzSAMBA excerpts.

Prepare creates strictly untimed projected chord runs and a protocol before
inference. Run supplies neither written grid timestamps nor tempo to the
aligners. This is easier than recognition and never promotes an arrangement.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
from pathlib import Path
import re
import time

import numpy as np

import alignment_screen
import chart_aligner
from candidates import nnls_chroma_adapter
import guarded_aligner
import guitarset_pilot as pilot
from guitarset_validation import checked_score
import lab

CONDITIONS = ('source-triad-runs', 'wrong-root-plus-one-semitone')
ALGORITHMS = ('frozen-nnls', 'guarded-nnls')
POLICY = lab.GENERATED / 'acceptance-development-v1/frozen-policy.json'
EXPECTED_FROZEN = {
    'experiments/analysis/chart_aligner.py': 'e21dc021cc8c508fea583ca4e11d293e6cfaf443535c4c370532cd9ff6a8a3e9',
    'experiments/analysis/guarded_aligner.py': 'f25536fdf9c56e5fdb0d03e8441c91a60ee91961272afa47011b5b815e24e6b0',
    'experiments/analysis/candidates/nnls_chroma_adapter.py': '6e0970496adb5d20c42dc3400d9a87db3d7b991463740d39813c5e621cd8a7a5',
    'experiments/generated/acceptance-development-v1/frozen-policy.json': '7a75786e45528622a86b5a6998452ef252c908f43a796c80d447c81b259c9ff3',
}


def safe_file(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError('Input must be a file inside its pack')
    return path


def projected_runs(reference: dict) -> list[dict]:
    """Preserve unknown/gap positions; merge adjacent identical triad targets.

    This uses the already declared source-field triad projection, not a new
    guessed conversion of rich/altered/slash symbols. Times stay here for scoring
    and are stripped before writing any aligner chart.
    """
    lab.validate_chart(reference)
    duration = reference['recording']['duration_seconds']
    runs, previous = [], 0.0
    for event in reference['chords']:
        start, end, label = event['start_seconds'], event['end_seconds'], event['label']
        if label not in ('N', 'X') and not re.fullmatch(r'[A-G][#b]?:(maj|min)', label):
            raise ValueError('Only declared major/minor projections and N/X are supported')
        if start < previous - 1e-9 or end > duration + 1e-9:
            raise ValueError('Reference exceeds its paired recording')
        additions = ([{'start_seconds': previous, 'end_seconds': start, 'label': 'X'}]
                     if start > previous else [])
        additions.append({'start_seconds': start, 'end_seconds': end, 'label': label})
        for row in additions:
            if runs and runs[-1]['label'] == row['label'] and abs(runs[-1]['end_seconds'] - row['start_seconds']) < 1e-9:
                runs[-1]['end_seconds'] = row['end_seconds']
            else:
                runs.append(row)
        previous = end
    if previous < duration:
        if runs and runs[-1]['label'] == 'X':
            runs[-1]['end_seconds'] = duration
        else:
            runs.append({'start_seconds': previous, 'end_seconds': duration, 'label': 'X'})
    if not runs:
        raise ValueError('Empty projected reference')
    return runs


def corrupt_root(label: str) -> str:
    if label in ('N', 'X'):
        return label
    match = re.fullmatch(r'([A-G])([#b]?):(maj|min)', label)
    if not match:
        raise ValueError('Wrong-root control needs supported triads')
    root = (chart_aligner.ROOTS[match[1]] + {'': 0, '#': 1, 'b': -1}[match[2]] + 1) % 12
    return lab.NOTES[root] + ':' + match[3]


def untimed(reference: dict, source_sha: str, condition: str) -> dict:
    if condition not in CONDITIONS:
        raise ValueError('Unknown predeclared chart condition')
    labels = [row['label'] for row in projected_runs(reference)]
    if condition == CONDITIONS[1]:
        labels = [corrupt_root(label) for label in labels]
    chart = {'schema_version': chart_aligner.SCHEMA,
             'recording': {key: reference['recording'][key] for key in ('id', 'title', 'audio_sha256')},
             'sequence': labels, 'mode': 'finite', 'start_policy': 'first', 'end_policy': 'last',
             'metadata': {'condition': condition, 'source_reference_sha256': source_sha,
                          'label_target': 'Previously declared publisher-source major/minor triad projection',
                          'unknowns': 'Unannotated gaps and unsupported projected positions retained as X',
                          'source_references': [{'dataset': 'JazzSAMBA publisher paired chart', 'reference_sha256': source_sha}],
                          'inference_contract': 'Ordered labels only; no source grid timestamps, tempo, key, bar fractions or durations'}}
    chart_aligner.validate_untimed_chart(chart)
    return chart


def write_new(path: Path, value: dict) -> None:
    chart_aligner.write_json_safely(path, value, [], overwrite=False)


def implementation_pins() -> dict:
    pins = {name: pilot.sha(lab.ROOT / name) for name in EXPECTED_FROZEN}
    if pins != EXPECTED_FROZEN:
        raise ValueError('Frozen candidate or acceptance policy changed')
    for name in ('experiments/analysis/jazzsamba_alignment_check.py',
                 'experiments/analysis/alignment_screen.py', 'experiments/analysis/guitarset_pilot.py',
                 'experiments/analysis/guitarset_validation.py',
                 'experiments/candidate-assets/nnls-chroma-evidence-native/buildinfo.json',
                 'experiments/candidate-assets/nnls-chroma-evidence-native/nnls-chroma-host',
                 'experiments/candidate-assets/chordino-native/nnls-chroma.dylib'):
        pins[name] = pilot.sha(lab.ROOT / name)
    return pins


def prepare(pack: Path, output: Path) -> dict:
    if output.exists():
        raise ValueError('Choose a fresh output directory before inference')
    manifest_path = safe_file(pack, 'manifest.json')
    manifest = json.loads(manifest_path.read_text())
    if len(manifest['cases']) != 3:
        raise ValueError('Bounded experiment requires the three frozen paired mixes')
    policy = json.loads(POLICY.read_text())
    pins = implementation_pins()
    case_rows, chart_rows = [], []
    for case in manifest['cases']:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', case['id']):
            raise ValueError('Unsafe case identifier')
        paths = {key: safe_file(pack, case[key]) for key in ('audio', 'reference', 'core_reference')}
        hashes = {key: pilot.sha(path) for key, path in paths.items()}
        if hashes['audio'] != case['source']['prepared_audio_sha256'] or hashes['reference'] != case['intended_reference_sha256']:
            raise ValueError('Publisher-paired input hash changed')
        reference = lab.load_chart(paths['core_reference'])
        signal, rate = lab.read_wav(paths['audio'])
        if reference['recording']['audio_sha256'] != hashes['audio'] or reference['recording']['sample_rate_hz'] != rate or reference['recording']['duration_seconds'] != len(signal) / rate:
            raise ValueError('Reference/audio exact pairing differs')
        rows = {}
        for condition in CONDITIONS:
            chart = untimed(reference, hashes['core_reference'], condition)
            relative = f"cases/{case['id']}/{condition}-untimed.json"
            chart_rows.append((relative, chart))
            rows[condition] = relative
        context = {}
        for candidate in ('baseline', 'btc', 'crema', 'chordmini', 'chordino'):
            path = safe_file(pack, f"cases/{case['id']}/{candidate}.json")
            context[candidate] = {'path': str(path.relative_to(pack)), 'sha256': pilot.sha(path)}
        case_rows.append({'id': case['id'], 'split': case['split'], 'inputs': case,
                          'source_hashes': hashes, 'untimed_charts': rows, 'raw_context': context})
    # Charts and hashes are fixed and published before any extraction/decoding.
    output.mkdir(parents=True)
    for relative, chart in chart_rows:
        write_new(output / relative, chart)
    for row in case_rows:
        row['untimed_sha256'] = {condition: pilot.sha(output / relative) for condition, relative in row['untimed_charts'].items()}
    protocol = {'schema_version': 'jazzsamba-conditional-alignment-protocol-1.0',
                'frozen_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'input_pack': str(pack), 'manifest_sha256': pilot.sha(manifest_path),
                'conditions': list(CONDITIONS), 'algorithms': list(ALGORITHMS),
                'frozen_policy_sha256': pilot.sha(POLICY), 'selected_guard_policy': policy['selected_policy'],
                'guarded_parameters': policy['parameters'],
                'baseline_parameters': {key: value for key, value in policy['parameters'].items() if key in ('hop_seconds', 'window_seconds', 'min_chord_seconds', 'transition_penalty', 'unknown_score', 'mismatch_margin', 'max_audio_seconds')},
                'implementation_sha256': pins, 'cases': case_rows,
                'boundary_tolerance_seconds': .15,
                'boundary_definition': 'Differing adjacent projected harmonies only; contiguous supported reference spans; N/X edges, identical repeated chords and gap edges excluded. Output N/X edges do not earn timing credit.',
                'no_tuning': True, 'source_timestamps_withheld': True,
                'training_exclusion_proven': False, 'arrangement_promotion': False,
                'reference_semantics': 'Written sheet-derived chart targets on publisher bar grids; not individually marked physical attacks or performed notes',
                'experiment_status': 'Retrospective method extension on already exposed three paired clips; split labels inherited, not fresh after raw-model outcomes'}
    write_new(output / 'protocol.json', protocol)
    return protocol


def boundary_score(reference: dict, prediction: dict) -> dict:
    runs = projected_runs(reference)
    known = [(row['start_seconds'], row['end_seconds']) for row in runs if row['label'] not in ('N', 'X')]
    expected = [second['start_seconds'] for first, second in zip(runs, runs[1:])
                if first['label'] not in ('N', 'X') and second['label'] not in ('N', 'X')
                and first['label'] != second['label'] and first['end_seconds'] == second['start_seconds']]
    actual = [second['start_seconds'] for first, second in zip(prediction['chords'], prediction['chords'][1:])
              if first['label'] not in ('N', 'X') and second['label'] not in ('N', 'X')
              and first['label'] != second['label'] and abs(first['end_seconds'] - second['start_seconds']) < 1e-9
              and any(start < second['start_seconds'] < end for start, end in known)]
    # Include boundaries exactly at the shared edge of two supported runs.
    actual += [second['start_seconds'] for first, second in zip(prediction['chords'], prediction['chords'][1:])
               if first['label'] not in ('N', 'X') and second['label'] not in ('N', 'X')
               and first['label'] != second['label'] and second['start_seconds'] in expected]
    actual = sorted(set(actual))
    matched = alignment_screen.optimal_boundary_matches(expected, actual, .15)
    p = len(matched) / len(actual) if actual else 0.0
    r = len(matched) / len(expected) if expected else 0.0
    errors = [row[2] for row in matched]
    return {'reference_supported_grid_boundaries': len(expected), 'predicted_supported_harmonic_boundaries': len(actual),
            'matched_grid_boundaries_150ms': len(matched), 'grid_boundary_precision_150ms': p,
            'grid_boundary_recall_150ms': r, 'grid_boundary_f1_150ms': 2 * p * r / (p + r) if p + r else 0.0,
            'matched_grid_boundary_mean_error_seconds': float(np.mean(errors)) if errors else None,
            'reference_grid_boundaries_seconds': expected, 'predicted_harmonic_boundaries_seconds': actual,
            'physical_attack_accuracy': 'not measured'}


def agreement(reference: dict, prediction: dict, candidate: str) -> dict:
    import mir_eval
    converted = copy.deepcopy(reference)
    for event in converted['chords']:
        event['native_label'] = pilot.to_harte(event['label'], native_harte=True)
    result = checked_score(converted, prediction, candidate)
    duration = reference['recording']['duration_seconds']
    refs, labels = pilot.complete_intervals(converted['chords'], duration, lambda row: row['native_label'])
    guesses, guess_labels = pilot.complete_intervals(prediction['chords'], duration, lambda row: pilot.prediction_label(row, candidate))
    intervals, rr, pp = mir_eval.util.merge_labeled_intervals(refs, labels, guesses, guess_labels)
    lengths = mir_eval.util.intervals_to_durations(intervals)
    scores = mir_eval.chord.majmin(rr, pp)
    harmonic = np.array([label not in ('N', 'X') for label in pp])
    result.update(retained_harmonic_seconds=float(lengths[harmonic].sum()),
                  retained_wrong_majmin_seconds=float(lengths[harmonic & (scores == 0)].sum()),
                  retained_correct_majmin_seconds=float(lengths[harmonic & (scores == 1)].sum()),
                  retained_harmonic_on_unknown_reference_seconds=float(lengths[harmonic & (scores < 0)].sum()))
    return result


def run(output: Path) -> dict:
    protocol_path = output / 'protocol.json'
    protocol = json.loads(protocol_path.read_text())
    if (output / 'report.json').exists():
        raise ValueError('Report already exists; frozen runs are not overwritten')
    if protocol['implementation_sha256'] != implementation_pins():
        raise ValueError('Runner/evaluator/runtime changed after freeze')
    pack = Path(protocol['input_pack'])
    if pilot.sha(pack / 'manifest.json') != protocol['manifest_sha256']:
        raise ValueError('Frozen manifest changed')
    # Check every input/chart/context before producing even the first output.
    for row in protocol['cases']:
        for key, expected in row['source_hashes'].items():
            if pilot.sha(safe_file(pack, row['inputs'][key])) != expected:
                raise ValueError('Frozen input changed')
        for condition, relative in row['untimed_charts'].items():
            if pilot.sha(safe_file(output, relative)) != row['untimed_sha256'][condition]:
                raise ValueError('Untimed input changed after freeze')
        for context in row['raw_context'].values():
            if pilot.sha(safe_file(pack, context['path'])) != context['sha256']:
                raise ValueError('Raw contextual prediction changed')
        evidence_path = output / 'cases' / row['id'] / 'nnls-evidence.json'
        paths = [evidence_path] + [output / 'cases' / row['id'] / f'{condition}-{algorithm}.json' for condition in CONDITIONS for algorithm in ALGORITHMS]
        if any(path.exists() or path.is_symlink() for path in paths):
            raise ValueError('Inference artifacts already exist; refusing overwrite')
    rows, context_rows, evidence_pins = [], [], []
    for row in protocol['cases']:
        audio = safe_file(pack, row['inputs']['audio'])
        evidence_path = output / 'cases' / row['id'] / 'nnls-evidence.json'
        evidence = nnls_chroma_adapter.extract(audio, row['id'])
        nnls_chroma_adapter.validate_evidence(evidence, audio)
        write_new(evidence_path, evidence)
        evidence_pins.append({'id': row['id'], 'sha256': pilot.sha(evidence_path),
                              'extraction_seconds': evidence['analysis']['runtime_seconds']})
        for condition in CONDITIONS:
            chart_path = safe_file(output, row['untimed_charts'][condition])
            for algorithm in ALGORITHMS:
                started = time.perf_counter()
                function = chart_aligner.align if algorithm == ALGORITHMS[0] else guarded_aligner.align
                parameters = protocol['baseline_parameters'] if algorithm == ALGORITHMS[0] else protocol['guarded_parameters']
                prediction = function(audio, chart_path, evidence_json=evidence_path, **parameters)
                relative = f"cases/{row['id']}/{condition}-{algorithm}.json"
                write_new(output / relative, prediction)
                # The timed reference is read only after this prediction exists.
                reference = lab.load_chart(safe_file(pack, row['inputs']['core_reference']))
                result = {'id': row['id'], 'split': row['split'], 'condition': condition, 'algorithm': algorithm,
                          'status': 'ok', 'prediction_sha256': pilot.sha(output / relative), 'prediction': relative,
                          'wall_seconds': time.perf_counter() - started,
                          'semantic': agreement(reference, prediction, algorithm),
                          'boundary': boundary_score(reference, prediction),
                          'diagnostics': prediction['alignment_evidence']['diagnostics']}
                rows.append(result)
                print(row['id'], condition, algorithm, 'ok', flush=True)
        reference = lab.load_chart(safe_file(pack, row['inputs']['core_reference']))
        for candidate, source in row['raw_context'].items():
            prediction = lab.load_chart(safe_file(pack, source['path']))
            context_rows.append({'id': row['id'], 'split': row['split'], 'candidate': candidate,
                                 'status': 'ok', 'prediction_sha256': source['sha256'],
                                 'semantic': agreement(reference, prediction, candidate),
                                 'task': 'Audio-only raw recognizer; no supplied label order'})
    summaries = []
    for condition in CONDITIONS:
        for algorithm in ALGORITHMS:
            for split in ('all', 'development', 'holdout'):
                selected = [row for row in rows if row['condition'] == condition and row['algorithm'] == algorithm and (split == 'all' or row['split'] == split)]
                total = sum(row['semantic']['duration_seconds'] for row in selected)
                result = {'condition': condition, 'algorithm': algorithm, 'split': split, 'cases': len(selected), 'duration_seconds': total}
                for metric in ('root', 'majmin'):
                    eligible = sum(row['semantic'][metric + '_eligible_seconds'] for row in selected)
                    result[metric] = sum((row['semantic'][metric] or 0) * row['semantic'][metric + '_eligible_seconds'] for row in selected) / eligible if eligible else None
                    result[metric + '_eligible_seconds'] = eligible
                    result[metric + '_reference_coverage'] = eligible / total if total else None
                for metric in ('estimated_unknown_seconds', 'retained_harmonic_seconds', 'retained_wrong_majmin_seconds', 'retained_correct_majmin_seconds', 'retained_harmonic_on_unknown_reference_seconds'):
                    result[metric] = sum(row['semantic'][metric] for row in selected)
                result['unvisited_sequence_positions'] = sum(len(row['diagnostics']['unvisited_sequence_indices']) for row in selected)
                result['matched_grid_boundaries_150ms'] = sum(row['boundary']['matched_grid_boundaries_150ms'] for row in selected)
                result['reference_supported_grid_boundaries'] = sum(row['boundary']['reference_supported_grid_boundaries'] for row in selected)
                result['predicted_supported_harmonic_boundaries'] = sum(row['boundary']['predicted_supported_harmonic_boundaries'] for row in selected)
                matched, expected, actual = (result[key] for key in ('matched_grid_boundaries_150ms', 'reference_supported_grid_boundaries', 'predicted_supported_harmonic_boundaries'))
                result['grid_boundary_f1_150ms'] = 2 * matched / (expected + actual) if expected + actual else 0.0
                summaries.append(result)
    report = {'schema_version': 'jazzsamba-conditional-alignment-check-1.0', 'date': '2026-10-12',
              'protocol': protocol, 'protocol_sha256': pilot.sha(protocol_path),
              'evidence': evidence_pins, 'summary': summaries, 'cases': rows, 'raw_context': context_rows,
              'limitations': ['Supplied projected labels/order make this a conditional timing task, distinct from audio-only recognition.',
                              'Written source grids do not establish individually performed chord attacks or playable beginner substitutions.',
                              'Unknown source positions and unannotated gaps are X; their duration is excluded from eligible agreement and reported separately.',
                              'Wrong-root chart can retain wrong cues despite heuristic guards; no arrangement is promoted.',
                              'Three previously exposed jazz clips are a retrospective extension, not a fresh rock test or pretrained-model exclusion guarantee.',
                              'Frozen thresholds and policy are unchanged; no source separation, key hints, tempo snapping, offset fitting or endpoint scaling.',
                              'Native chroma uses about 743ms support and 93ms hop at 22050Hz; 25ms decoder sampling adds no acoustic resolution.',
                              'Source media/annotations remain local and untracked; dataset licence clarification remains pending.']}
    write_new(output / 'report.json', report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run'))
    parser.add_argument('--pack', type=Path, default=lab.GENERATED / 'jazzsamba-reference-v1')
    parser.add_argument('--output', type=Path, default=lab.GENERATED / 'jazzsamba-alignment-v1')
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.pack.resolve(), args.output.resolve())
        print('Frozen protocol:', args.output / 'protocol.json', result['frozen_at_utc'])
    else:
        result = run(args.output.resolve())
        print(json.dumps([row for row in result['summary'] if row['split'] == 'all'], indent=2))


if __name__ == '__main__':
    main()
