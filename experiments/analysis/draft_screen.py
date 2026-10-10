"""Evaluate automatic draft warnings against existing labels, never model consensus gold."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

import guitarset_pilot as pilot
import lab


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def common_timeline(reference: dict, primary: dict, secondary: dict,
                    primary_candidate: str = 'crema', secondary_candidate: str = 'chordino'):
    """Exact piecewise intervals; no sampling grid or guessed timing adjustment."""
    for chart in (reference, primary, secondary):
        lab.validate_chart(chart)
        audio_hash = chart['recording'].get('audio_sha256')
        if not isinstance(audio_hash, str) or len(audio_hash) != 64 or any(c not in '0123456789abcdef' for c in audio_hash):
            raise ValueError('Every evaluation chart requires an audio SHA-256')
    duration = reference['recording']['duration_seconds']
    for chart in (primary, secondary):
        if chart['recording']['id'] != reference['recording']['id']:
            raise ValueError('Recording ID mismatch')
        if chart['recording']['sample_rate_hz'] != reference['recording']['sample_rate_hz']:
            raise ValueError('Recording sample rate mismatch')
        if abs(chart['recording']['duration_seconds'] - duration) > 1 / 22050:
            raise ValueError('Recording duration mismatch')
        if reference['recording'].get('audio_sha256') != chart['recording'].get('audio_sha256'):
            raise ValueError('Recording audio hash mismatch')
    timelines = [pilot.complete_intervals(chart['chords'], duration, label)
                 for chart, label in [
                     (reference, lambda e: pilot.to_harte(e['native_label'], True)),
                     (primary, lambda e: pilot.prediction_label(e, primary_candidate)),
                     (secondary, lambda e: pilot.prediction_label(e, secondary_candidate))]]
    points = sorted({float(t) for intervals, _ in timelines for t in intervals.flat})
    intervals = np.column_stack([points[:-1], points[1:]])
    centers = intervals.mean(axis=1)
    labels = []
    for original, names in timelines:
        indices = np.searchsorted(original[:, 1], centers, side='right')
        labels.append([names[i] for i in indices])
    return intervals, *labels


def flag_union(flags: list[dict], duration: float) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for flag in sorted(flags, key=lambda f: f['start_seconds']):
        start, end = float(flag['start_seconds']), float(flag['end_seconds'])
        if not (0 <= start < end <= duration):
            raise ValueError('Warning interval outside recording')
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(end, result[-1][1]))
        else:
            result.append((start, end))
    return result


def overlap_seconds(intervals: np.ndarray, spans: list[tuple[float, float]]) -> np.ndarray:
    amount = np.zeros(len(intervals))
    for start, end in spans:
        amount += np.maximum(0, np.minimum(intervals[:, 1], end) - np.maximum(intervals[:, 0], start))
    return amount


def score_pair(reference: dict, primary: dict, secondary: dict, flags: list[dict] | None = None,
               primary_candidate: str = 'crema', secondary_candidate: str = 'chordino') -> dict:
    """Duration-based warning enrichment. Inherited labels cannot judge physical onset flags."""
    import mir_eval
    intervals, refs, first, second = common_timeline(reference, primary, secondary,
                                                  primary_candidate, secondary_candidate)
    durations = intervals[:, 1] - intervals[:, 0]
    duration = reference['recording']['duration_seconds']
    spans = flag_union(flags or [], duration)
    flagged = overlap_seconds(intervals, spans)
    result = {'duration_seconds': duration, 'flagged_seconds': float(flagged.sum()),
              'flagged_fraction': float(flagged.sum() / duration), 'flag_union': spans}
    for name, metric in [('root', mir_eval.chord.root), ('majmin', mir_eval.chord.majmin)]:
        truth = metric(refs, first)
        truth[np.asarray(first) == 'X'] = np.where(truth[np.asarray(first) == 'X'] >= 0, 0,
                                                 truth[np.asarray(first) == 'X'])
        eligible = truth >= 0
        correct = eligible & (truth == 1)
        error = eligible & (truth == 0)
        forward, backward = metric(first, second), metric(second, first)
        pair_eligible = (forward >= 0) & (backward >= 0) & (np.asarray(first) != 'X') & (np.asarray(second) != 'X')
        agrees = pair_eligible & (forward == 1) & (backward == 1)
        disagrees = pair_eligible & ~agrees
        seconds = float(durations[eligible].sum())
        error_seconds = float(durations[error].sum())
        disagreement_seconds = float(durations[eligible & disagrees].sum())
        disagreement_error = float(durations[error & disagrees].sum())
        shared_wrong = float(durations[error & agrees].sum())
        flagged_eligible = float(flagged[eligible].sum())
        flagged_error = float(flagged[error].sum())
        result[name] = {
            'primary_accuracy': float(durations[correct].sum() / seconds) if seconds else None,
            'eligible_seconds': seconds, 'reference_coverage_fraction': seconds / duration,
            'primary_error_seconds': error_seconds,
            'raw_pair_compared_seconds_on_reference_eligible': float(durations[eligible & pair_eligible].sum()),
            'raw_disagreement_seconds_on_reference_eligible': disagreement_seconds,
            'raw_disagreement_error_seconds': disagreement_error,
            'raw_disagreement_error_capture_fraction': disagreement_error / error_seconds if error_seconds else None,
            'raw_disagreement_error_precision': disagreement_error / disagreement_seconds if disagreement_seconds else None,
            'raw_disagreement_correct_primary_seconds': float(durations[correct & disagrees].sum()),
            'shared_agreement_wrong_seconds': shared_wrong,
            'shared_agreement_wrong_fraction_of_primary_errors': shared_wrong / error_seconds if error_seconds else None,
            'flagged_reference_eligible_seconds': flagged_eligible,
            'flagged_primary_error_seconds': flagged_error,
            'flagged_primary_correct_seconds': float(flagged[correct].sum()),
            'flagged_label_error_capture_fraction': flagged_error / error_seconds if error_seconds else None,
            'flagged_label_error_enrichment_fraction': flagged_error / flagged_eligible if flagged_eligible else None,
        }
    return result


def aggregate(rows: list[dict], reference_kind: str) -> dict:
    chosen = [row for row in rows if row['reference_kind'] == reference_kind]
    total = sum(row['metrics']['duration_seconds'] for row in chosen)
    flagged = sum(row['metrics']['flagged_seconds'] for row in chosen)
    result = {'reference_kind': reference_kind, 'successful_cases': len(chosen),
              'duration_seconds': total, 'flagged_seconds': flagged,
              'flagged_fraction': flagged / total}
    for metric in ('root', 'majmin'):
        values = [row['metrics'][metric] for row in chosen]
        summed = {key: sum(value[key] for value in values) for key in values[0]
                  if '_seconds' in key}
        eligible, errors = summed['eligible_seconds'], summed['primary_error_seconds']
        raw, raw_errors = summed['raw_disagreement_seconds_on_reference_eligible'], summed['raw_disagreement_error_seconds']
        flagged_eligible, flagged_errors = summed['flagged_reference_eligible_seconds'], summed['flagged_primary_error_seconds']
        result[metric] = {**summed,
            'primary_accuracy': 1 - errors / eligible if eligible else None,
            'reference_coverage_fraction': eligible / total,
            'raw_disagreement_error_capture_fraction': raw_errors / errors if errors else None,
            'raw_disagreement_error_precision': raw_errors / raw if raw else None,
            'shared_agreement_wrong_fraction_of_primary_errors': summed['shared_agreement_wrong_seconds'] / errors if errors else None,
            'flagged_label_error_capture_fraction': flagged_errors / errors if errors else None,
            'flagged_label_error_enrichment_fraction': flagged_errors / flagged_eligible if flagged_eligible else None}
    return result


def synthetic_checks(compare) -> list[dict]:
    def chart(label: str, candidate: str, native: str | None = None):
        return {'schema_version': '1.0', 'recording': {'id': 'semantic-check', 'title': 'known labels',
                'duration_seconds': 10, 'sample_rate_hz': 22050, 'audio_sha256': 'a' * 64},
                'analysis': {'id': candidate, 'algorithm': candidate, 'version': 'semantic-test', 'runtime_seconds': 0},
                'chords': [{'start_seconds': 0, 'end_seconds': 10, 'label': label, 'native_label': native or label}]}
    scenarios = [
        ('same-root-major-minor-disagreement', 'C:maj', 'C', 'C:maj', 'Cm', 0.0, 1.0),
        ('seventh-extension-hidden-by-triad-agreement', 'C:7', 'C', 'C:maj', 'C7', 1.0, 0.0),
        ('shared-wrong-consensus', 'F:maj', 'C', 'C:maj', 'C', 1.0, 0.0),
    ]
    checks = []
    import mir_eval
    for name, ref_label, p_label, p_native, s_label, expected_pair, expected_sevenths in scenarios:
        reference, primary, secondary = chart(ref_label, 'reference'), chart(p_label, 'crema', p_native), chart(s_label, 'chordino')
        evidence = compare(primary, secondary)
        metrics = score_pair(reference, primary, secondary, evidence['flags'])
        pair = mir_eval.chord.majmin([p_native], [pilot.to_harte(s_label)])[0]
        sevenths = mir_eval.chord.sevenths([ref_label], [p_native])[0]
        if pair != expected_pair or sevenths != expected_sevenths:
            raise ValueError('Semantic screen failed: ' + name)
        checks.append({'id': name, 'status': 'pass', 'known_reference': ref_label,
                       'primary': p_native, 'secondary': pilot.to_harte(s_label),
                       'pair_triads_agree': bool(pair == 1), 'primary_sevenths_correct': bool(sevenths == 1),
                       'warning_count': len(evidence['flags']), 'metrics': metrics})
    return checks


def run(pilot_root: Path, previous_report: Path) -> dict:
    import automatic_drafts
    import mir_eval
    manifest = json.loads((pilot_root / 'manifest.json').read_text())
    if len(manifest['cases']) != 6 or {c['original_id'] for c in manifest['cases']} != set(pilot.SELECTED):
        raise ValueError('Screen requires the original six preselected GuitarSet recordings')
    rows, inputs = [], []
    comparison_parameters = None
    for case in manifest['cases']:
        folder = pilot_root / 'cases' / case['id']
        audio = (pilot_root / case['audio']).resolve()
        if not audio.is_relative_to(pilot_root.resolve()) or digest(audio) != case['source']['prepared_audio_sha256']:
            raise ValueError('Changed or out-of-suite audio')
        primary, secondary = lab.load_chart(folder / 'crema.json'), lab.load_chart(folder / 'chordino.json')
        if primary['recording']['audio_sha256'] != digest(audio):
            raise ValueError('Prediction audio pairing failed')
        evidence = automatic_drafts.compare_charts(primary, secondary)
        comparison_parameters = evidence['parameters']
        for kind, path_key, sha_key in [('intended', 'reference', 'intended_reference_sha256'),
                                       ('performed', 'performed_reference', 'performed_reference_sha256')]:
            ref_path = (pilot_root / case[path_key]).resolve()
            if not ref_path.is_relative_to(pilot_root.resolve()) or digest(ref_path) != case[sha_key]:
                raise ValueError('Changed or out-of-suite reference')
            reference = lab.load_chart(ref_path)
            metrics = score_pair(reference, primary, secondary, evidence['flags'])
            rows.append({'case_id': case['id'], 'reference_kind': kind, 'status': 'ok',
                         'warning_count': len(evidence['flags']), 'review_point_count': len(evidence['review_points']),
                         'metrics': metrics})
        inputs.append({'case_id': case['id'], 'audio_sha256': digest(audio),
                       'primary_sha256': digest(folder / 'crema.json'), 'secondary_sha256': digest(folder / 'chordino.json'),
                       'intended_reference_sha256': case['intended_reference_sha256'],
                       'performed_reference_sha256': case['performed_reference_sha256']})
    summaries = [aggregate(rows, kind) for kind in ('intended', 'performed')]
    previous = json.loads(previous_report.read_text())
    for summary in summaries:
        old = next(row for row in previous['summary']
                   if row['candidate'] == 'crema' and row['reference_kind'] == summary['reference_kind'])
        for metric in ('root', 'majmin'):
            if abs(old[metric] - summary[metric]['primary_accuracy']) > 1e-10:
                raise ValueError('Cached primary score differs from original pilot')
    checks = synthetic_checks(automatic_drafts.compare_charts)
    return {'schema_version': 'draft-screen-1.0', 'comparison': 'CREMA primary; Chordino disagreement evidence; no vote or label replacement',
            'environment': {'python': sys.version.split()[0], 'numpy': np.__version__, 'mir_eval': mir_eval.__version__},
            'gates': {'all_six_exact_inputs_verified': True, 'all_twelve_reference_comparisons_completed': True,
                      'original_primary_scores_reproduced': True, 'semantic_edge_cases': len(checks),
                      'manual_annotations_required_to_complete_screen': False,
                      'production_accuracy_gate_passed': False},
            'comparison_parameters': comparison_parameters,
            'automatic_drafts_module_sha256': digest(Path(automatic_drafts.__file__)),
            'evaluation_module_sha256': digest(Path(__file__)),
            'manifest_sha256': digest(pilot_root / 'manifest.json'),
            'summary': summaries, 'cases': rows, 'synthetic_semantic_checks': checks, 'inputs': inputs,
            'previous_report_sha256': digest(previous_report),
            'limitations': ['Six acoustic guitar recordings from one dataset; not commercial full-band mix accuracy.',
                'Performed roots and segmentation inherit the instructed lead sheet; no physical onset accuracy tested.',
                'Warning enrichment compares labels only. Timing flags on correct-label spans are not proven false positives.',
                'Model agreement is not ground truth; major/minor agreement does not certify sevenths, suspensions or basses.',
                'Cached predictions reused; no new model training, tuning, inference or source separation.']}


def markdown(report: dict) -> str:
    def pct(value): return 'n/a' if value is None else f'{100 * value:.1f}%'
    lines = ['# Automated draft screening', '',
             'The automatic workflow uses CREMA as an experimental primary draft and Chordino as disagreement evidence. '
             'No manual annotations are needed for this screen. These are unchanged cached predictions; warnings do not replace chords.', '',
             'All six preselected GuitarSet recordings passed pairing/hash checks, all 12 intended/performed comparisons completed, '
             'and primary scores exactly reproduced the previous pilot. This passes workflow checks, not a production accuracy gate.', '',
             '| Reference | Primary major/minor | Eligible coverage | Raw disagreements capture primary errors | Raw disagreement error precision | Errors surviving agreement |',
             '|---|---:|---:|---:|---:|---:|']
    for row in report['summary']:
        m = row['majmin']
        lines.append(f"| {row['reference_kind'].title()} | {pct(m['primary_accuracy'])} | {pct(m['reference_coverage_fraction'])} | "
                     f"{pct(m['raw_disagreement_error_capture_fraction'])} | {pct(m['raw_disagreement_error_precision'])} | "
                     f"{pct(m['shared_agreement_wrong_fraction_of_primary_errors'])} |")
    lines += ['', 'Scores are duration weighted on `mir_eval.majmin` eligible reference spans. Raw disagreement precision means '
              'the fraction of disagreement time containing a primary label error. Other disagreement time has a correct primary label '
              '(the secondary is wrong or differs). It is an uncertainty signal, not an instruction to accept the secondary.', '',
              'Raw disagreement here uses mutually eligible `mir_eval` root/major-minor comparisons, including explicit no-chord differences '
              'and excluding unknown predictions. The playback evidence reports its own harmonic-only agreement denominator; these are '
              'different measures with separate coverage. Neither is a correctness score without the dataset reference.', '',
              '| Reference | Warning time / audio | Warnings capture primary quality errors | Label-error fraction within warnings | Correct-primary time inside warnings |',
              '|---|---:|---:|---:|---:|']
    for row in report['summary']:
        m = row['majmin']
        lines.append(f"| {row['reference_kind'].title()} | {pct(row['flagged_fraction'])} | "
                     f"{pct(m['flagged_label_error_capture_fraction'])} | {pct(m['flagged_label_error_enrichment_fraction'])} | "
                     f"{m['flagged_primary_correct_seconds']:.2f} s |")
    lines += ['', 'Warning workload is the union of all emitted warning intervals, including timing and unknown/short-event evidence. '
              'Intervals overlap only once. This label-error enrichment is deliberately not called timing accuracy or warning precision: '
              'a timing warning can be useful even where the chord label is correct. Short disagreement intervals may be omitted by the display thresholds.', '',
              'Three deterministic known-label checks pass: same-root major/minor disagreement; C7 versus C major sharing the same triad; '
              'and two algorithms agreeing on the same wrong chord. The latter two explicitly demonstrate limits of agreement. '
              'These are semantic guard tests, not acoustic recognition tests.', '',
              'GuitarSet totals 182.36 seconds of acoustic guitar. Performed roots and segmentation inherit the instructed lead sheet. '
              'Physical onset timing, full-band YouTube accuracy, extension accuracy and calibrated confidence remain unmeasured. '
              'Major/minor coverage differs between intended and performed annotations, so their scores have different denominators. '
              'The original dataset and model-overlap qualifications remain in [GUITARSET_PILOT.md](GUITARSET_PILOT.md).', '',
              'The finite automatic gates are exact audio/chart pairing, valid ordered in-range timelines, complete cached comparisons, '
              'original-score parity and the semantic edge-case checks. User listening feedback is optional and can focus on a few flagged moments; '
              'full manual transcription is not a gate for the experimental play-along.', '',
              '## Reproduce', '', 'From the repository root with the existing verified GuitarSet pilot assets and pinned evaluation environment:', '',
              '```sh', '.venv-crema/bin/python experiments/analysis/draft_screen.py',
              '.venv-crema/bin/python -m unittest discover -s experiments/analysis/tests -p test_draft_screen.py', '```', '',
              'A separate `.venv-pilot` with `requirements-pilot.txt` can replace `.venv-crema`. '
              'The script reuses saved JSON; no neural model runtime is needed. Default output is `docs/DRAFT_SCREEN.json` and this Markdown. '
              'The JSON preserves input hashes, exact per-case seconds, roots, warning counts and all three known-label cases.', '']
    return '\n'.join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pilot-root', type=Path, default=lab.GENERATED / 'guitarset-pilot')
    parser.add_argument('--previous-report', type=Path, default=lab.ROOT / 'docs/GUITARSET_PILOT.json')
    parser.add_argument('--output', type=Path, default=lab.ROOT / 'docs/DRAFT_SCREEN.json')
    args = parser.parse_args()
    report = run(args.pilot_root, args.previous_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    args.output.with_suffix('.md').write_text(markdown(report))
    print(json.dumps({'gates': report['gates'], 'summary': report['summary']}, indent=2))


if __name__ == '__main__':
    main()
