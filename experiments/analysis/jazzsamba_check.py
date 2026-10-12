"""Score unchanged draft models against publisher-paired written jazz charts.

References preserve original symbols separately from supported Harte labels.
This is chart-target agreement, not note-level performed harmony or rock accuracy.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

import guitarset_pilot as pilot
from guitarset_validation import checked_score
import lab


def validate_core_reference(rich: dict, core: dict) -> None:
    """Reconstruct declared triad targets from immutable rich-source fields."""
    if core['recording'] != rich['recording'] or len(core['chords']) != len(rich['chords']):
        raise ValueError('Core/rich reference recording or interval count differs')
    for original, projected in zip(rich['chords'], core['chords']):
        if ({k: v for k, v in original.items() if k != 'label'}
                != {k: v for k, v in projected.items() if k != 'label'}):
            raise ValueError('Core reference altered source fields or interval timing')
        fields = original['source_fields']
        no_chord = fields['is_no_chord']
        if no_chord not in ('True', 'False'):
            raise ValueError('Invalid source no-chord flag')
        expected = ('N' if no_chord == 'True' else
                    fields['root'] + ':' + fields['triad'] if fields['triad'] in ('maj', 'min') else 'X')
        if projected['label'] != expected:
            raise ValueError('Core label differs from frozen declared source-triad projection')


def harte_reference(reference: dict) -> dict:
    result = copy.deepcopy(reference)
    for event in result['chords']:
        # The producer's declared conversion uses X for unsupported rich symbols.
        # Original dataset spellings remain byte-identical in the saved reference.
        event['source_native_symbol'] = event.get('native_label')
        event['native_label'] = pilot.to_harte(event['label'], native_harte=True)
    return result


def evaluate(pack: Path, output: Path, protocol_path: Path | None = None) -> dict:
    if output.exists():
        raise ValueError('Choose a fresh report path')
    manifest_path = pack / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    protocol_path = protocol_path or pack / 'chord-protocol.json'
    protocol = json.loads(protocol_path.read_text())
    if (pilot.sha(manifest_path) != protocol['manifest_sha256']
            or pilot.sha(pack / 'selection.json') != protocol['source_selection_sha256']
            or pilot.sha(pack / 'audio-only-inference-manifest.json') != protocol['audio_only_manifest_sha256']):
        raise ValueError('Frozen source selection/manifest changed')
    for name, expected in protocol['frozen_files'].items():
        # Saved predictions carry model provenance; cached rescoring needs source
        # code integrity but not an installed inference runtime or checkpoint.
        if name.startswith('.venv-') or name.startswith('experiments/candidate-assets/'):
            continue
        if pilot.sha(lab.ROOT / name) != expected:
            raise ValueError('Frozen candidate/evaluator changed')
    rows, pins = [], []
    for case in manifest['cases']:
        audio = pack / case['audio']
        if pilot.sha(audio) != case['source']['prepared_audio_sha256']:
            raise ValueError('Prepared audio hash mismatch')
        if pilot.sha(pack / case['reference']) != case['intended_reference_sha256']:
            raise ValueError('Intended reference hash mismatch')
        validate_core_reference(lab.load_chart(pack / case['reference']),
                                lab.load_chart(pack / case['core_reference']))
        for kind, key in (('supported-rich-Harte', 'reference'),
                          ('declared-major-minor-triad-projection', 'core_reference')):
            ref_path = pack / case[key]
            reference = harte_reference(lab.load_chart(ref_path))
            for candidate in protocol['candidates']:
                path = pack / 'cases' / case['id'] / (candidate + '.json')
                row = {'id': case['id'], 'split': case['split'], 'reference_kind': kind,
                       'candidate': candidate, 'status': 'ok', 'reference_sha256': pilot.sha(ref_path)}
                try:
                    prediction = lab.load_chart(path)
                    row.update(checked_score(reference, prediction, candidate))
                    row['prediction_sha256'] = pilot.sha(path)
                    row['analysis_provenance'] = prediction['analysis']
                except Exception as error:
                    row.update(status='error', error=type(error).__name__ + ': ' + str(error))
                rows.append(row)
        pins.append({'id': case['id'], 'source': case['source']})
    summaries = []
    for split in ('all', 'development', 'holdout'):
        for kind in protocol['reference_conditions']:
            for candidate in protocol['candidates']:
                requested = [r for r in rows if r['candidate'] == candidate and r['reference_kind'] == kind
                             and (split == 'all' or r['split'] == split)]
                good = [r for r in requested if r['status'] == 'ok']
                total = sum(r['duration_seconds'] for r in good)
                row = {'split': split, 'reference_kind': kind, 'candidate': candidate,
                       'requested_cases': len(requested), 'successful_cases': len(good),
                       'failed_cases': len(requested) - len(good), 'scored_audio_seconds': total}
                for metric in ('root', 'majmin', 'root_chord_only', 'majmin_chord_only'):
                    eligible = sum(r[metric + '_eligible_seconds'] for r in good)
                    row[metric] = (sum((r[metric] or 0) * r[metric + '_eligible_seconds'] for r in good)
                                   / eligible if eligible else None)
                    row[metric + '_eligible_seconds'] = eligible
                    row[metric + '_reference_coverage'] = eligible / total if total else None
                row['inference_seconds'] = sum(r['analysis_runtime_seconds'] for r in good)
                summaries.append(row)
    result = {'schema_version': 'jazzsamba-chord-check-1.0',
              'date': '2026-10-12', 'protocol': protocol,
              'protocol_sha256': pilot.sha(protocol_path),
              'evaluator_sha256': pilot.sha(Path(__file__)), 'source_pins': pins,
              'summary': summaries, 'cases': rows,
              'limitations': ['Written chart targets aligned to musician-authored bar grids, not individually marked performed notes or physical chord attacks.',
                              'Unsupported rich/slash/altered symbols use X; eligible reference coverage is shown beside every score.',
                              'Triad projection is a separately declared easier target; it does not improve the recognizer or prove playable substitutions.',
                              'Three first-60-second publisher web encodings are jazz mixes, not rock repertoire or universal full-song accuracy.',
                              'Experiment holdout is not proof of exclusion from pretrained model training.',
                              'Dataset audio reuse licence not retrieved; local publisher-released research, no media redistributed.']}
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=lab.GENERATED / 'jazzsamba-reference-v1')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--protocol', type=Path)
    args = parser.parse_args()
    result = evaluate(args.pack.resolve(), args.output.resolve(),
                      args.protocol.resolve() if args.protocol else None)
    print(json.dumps([row for row in result['summary'] if row['split'] == 'all'], indent=2))
    if any(row['status'] != 'ok' for row in result['cases']):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
