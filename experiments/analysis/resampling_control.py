"""Separately frozen Julius round-trip control; original separation protocol unchanged."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import time

import numpy as np

import separation_check as separation

CONDITION = 'resampling-only'


def require_unexposed(pack: Path) -> None:
    if (pack / 'btc-attempt.json').exists() or list(pack.glob('cases/*/minus-*-btc.json')):
        raise ValueError('Freeze extension before any derivative BTC output is exposed')


def roundtrip(mono, rate: int):
    import torch
    import julius
    signal = np.asarray(mono, dtype=np.float32)
    if signal.ndim != 1 or rate != 22050:
        raise ValueError('Expected the paired mono 22050 Hz source')
    separation.amplitude(signal)
    torch.set_num_threads(1)
    stereo = torch.from_numpy(signal).unsqueeze(0).expand(2, -1)
    native = julius.resample_frac(stereo, rate, 44100)
    result = julius.resample_frac(native.mean(0), 44100, rate).numpy()
    if native.shape != (2, len(signal) * 2) or result.shape != signal.shape:
        raise ValueError('Round trip changed source frames; no trim/pad permitted')
    separation.amplitude(result)
    return result


def prepare(pack: Path, expected: str) -> dict:
    import soundfile as sf
    require_unexposed(pack)
    original = separation.validate_protocol(pack, expected, require_runtime=True)
    root = pack / 'resampling-control'
    if root.exists():
        raise ValueError('Preserve the existing control declaration/attempt')
    root.mkdir()
    cases = []
    for case in original['cases']:
        start = time.perf_counter()
        mono, rate = sf.read(pack / case['audio'], dtype='float32')
        signal = roundtrip(mono, rate)
        audio = root / (case['id'] + '.wav')
        sf.write(audio, signal, rate, subtype='FLOAT')
        decoded, saved_rate = sf.read(audio, dtype='float32')
        if saved_rate != rate or not np.array_equal(signal, decoded):
            raise ValueError('Float control WAV publication changed samples')
        difference = signal.astype(np.float64) - mono
        cases.append({'id': case['id'], 'condition': CONDITION,
                      'audio': str(audio.relative_to(pack)), 'audio_sha256': separation.pilot.sha(audio),
                      'source_audio_sha256': case['audio_sha256'], 'sample_rate_hz': rate,
                      'frames': len(signal), 'duration_seconds': len(signal) / rate,
                      'preparation_seconds': time.perf_counter() - start,
                      'original_diagnostics': separation.amplitude(mono),
                      'output_diagnostics': separation.amplitude(signal),
                      'difference_diagnostics': separation.amplitude(difference),
                      'difference_rms_ratio': separation.amplitude(difference)['rms'] / separation.amplitude(mono)['rms']})
    require_unexposed(pack)
    packet = {'schema_version': 'resampling-control-protocol-1.0', 'date': '2026-10-12',
              'frozen_before': 'All six derivative BTC runs and all three resampling-only BTC outputs; prior original-mixture results exposed',
              'selection': 'All three original excerpts; retrospective diagnostic, no fresh holdout',
              'base_protocol_sha256': expected, 'condition': CONDITION,
              'source_sha256': separation.pilot.sha(Path(__file__)),
              'settings': {'preparation': original['settings']['resampling'], 'no_separator': True,
                           'storage': original['settings']['storage'], 'btc_threads': 4,
                           'btc_model_and_decoder': 'unchanged original frozen BTC adapter/checkpoint',
                           'no_gain_clipping_trimming_padding_offset': True},
              'cases': cases, 'accepted_for_playback': False}
    separation.write(root / 'extension.json', packet)
    return {'extension_sha256': separation.pilot.sha(root / 'extension.json'), 'cases': len(cases)}


def validate(pack: Path, expected: str, extension_hash: str) -> dict:
    base = separation.validate_protocol(pack, expected)
    path = pack / 'resampling-control/extension.json'
    if separation.pilot.sha(path) != extension_hash:
        raise ValueError('Frozen resampling control hash mismatch')
    packet = separation.read(path)
    if (packet['base_protocol_sha256'] != expected or packet['condition'] != CONDITION
            or packet['source_sha256'] != separation.pilot.sha(Path(__file__))
            or packet['accepted_for_playback'] is not False):
        raise ValueError('Frozen resampling source/condition/parent identity differs')
    if {r['id'] for r in packet['cases']} != {r['id'] for r in base['cases']}:
        raise ValueError('Resampling control must cover the same three sources')
    for row in packet['cases']:
        if separation.pilot.sha(separation.confined(pack, row['audio'])) != row['audio_sha256']:
            raise ValueError('Frozen resampling-only audio changed')
    return packet


def infer(pack: Path, expected: str, extension_hash: str) -> dict:
    from candidates import btc_adapter
    packet = validate(pack, expected, extension_hash)
    base = separation.validate_protocol(pack, expected)
    if separation.pinned_runtime() != base['btc_runtime']:
        raise ValueError('BTC runtime changed')
    output = pack / 'resampling-control/btc-attempt.json'
    if output.exists():
        raise ValueError('Preserve existing BTC control attempt')
    results = []; started = time.perf_counter()
    for case in packet['cases']:
        row = {'id': case['id'], 'condition': CONDITION, 'status': 'error'}
        try:
            audio = separation.confined(pack, case['audio'])
            prediction = btc_adapter.infer(audio, case['id'],
                                           separation.ROOT / 'experiments/candidate-assets/btc-ismir19', 4)
            prediction['analysis']['source_separation'] = {
                'condition': CONDITION, 'protocol_sha256': extension_hash,
                'inference_inputs_sha256': extension_hash, 'source_audio_sha256': case['source_audio_sha256'],
                'accepted_for_playback': False}
            prediction['analysis']['resampling_control'] = 'Julius round trip only; no separator/model stems'
            path = pack / 'resampling-control' / (case['id'] + '-btc.json')
            separation.write(path, prediction)
            row.update(status='ok', prediction=str(path.relative_to(pack)),
                       prediction_sha256=separation.pilot.sha(path), inference_seconds=prediction['analysis']['runtime_seconds'])
            print(f"BTC resampling control {case['id']}: {row['inference_seconds']:.3f}s", flush=True)
        except Exception as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
            print(f"BTC resampling control {case['id']}: FAILED {row['error']}", flush=True)
        results.append(row)
    report = {'schema_version': 'resampling-btc-attempt-1.0', 'base_protocol_sha256': expected,
              'extension_sha256': extension_hash, 'cases': results, 'runtime_seconds': time.perf_counter() - started,
              'failed_cases': sum(r['status'] != 'ok' for r in results), 'accepted_for_playback': False}
    separation.write(output, report)
    validate(pack, expected, extension_hash)
    return report


def score(pack: Path, expected: str, extension_hash: str, base_report: Path, output: Path) -> dict:
    import mir_eval
    if mir_eval.__version__ != '0.8.2' or output.exists():
        raise ValueError('Use mir_eval0.8.2 and a fresh merged report path')
    extension = validate(pack, expected, extension_hash)
    base = separation.validate_protocol(pack, expected); result = separation.read(base_report)
    if result['protocol_sha256'] != expected or result['accepted_for_playback'] is not False:
        raise ValueError('Original separation report protocol/acceptance differs')
    attempts_path = pack / 'resampling-control/btc-attempt.json'; attempts = separation.read(attempts_path)
    if attempts['extension_sha256'] != extension_hash or attempts['base_protocol_sha256'] != expected:
        raise ValueError('Saved control attempt identity differs')
    outputs = {r['id']: r for r in attempts['cases']}; controls = {r['id']: r for r in extension['cases']}
    rows = []
    for case in base['cases']:
        rich = separation.lab.load_chart(pack / case['reference'])
        core = separation.lab.load_chart(pack / case['core_reference'])
        separation.jazz.validate_core_reference(rich, core)
        for kind, reference in zip(separation.KINDS, (rich, core)):
            reference = separation.jazz.harte_reference(reference)
            row = {'id': case['id'], 'reference_kind': kind, 'condition': CONDITION,
                   'status': 'error', 'accepted_for_playback': False}
            try:
                attempt = outputs[case['id']]; control = controls[case['id']]
                if attempt['status'] != 'ok':
                    raise ValueError('Control detector failure retained in saved attempt')
                prediction_path = separation.confined(pack, attempt['prediction'])
                if separation.pilot.sha(prediction_path) != attempt['prediction_sha256']:
                    raise ValueError('Saved control prediction changed')
                prediction = separation.lab.load_chart(prediction_path)
                separation.validate_derivative(reference, prediction, case, control, extension_hash, extension_hash)
                row.update(separation.pilot.score(reference, prediction, 'btc'), status='ok',
                           separation_seconds=0, preparation_seconds=control['preparation_seconds'],
                           cached_control=False, prediction_sha256=separation.pilot.sha(prediction_path),
                           analysis_provenance=prediction['analysis'])
            except Exception as error:
                row['error'] = type(error).__name__ + ': ' + str(error)
            rows.append(row)
    result['resampling_control'] = {'extension': extension, 'extension_sha256': extension_hash,
            'btc_attempt_sha256': separation.pilot.sha(attempts_path), 'btc_batch_seconds': attempts['runtime_seconds'],
            'summary': [r for r in summarize_controls(rows)], 'cases': rows}
    result['combined_cases'] = result['cases'] + rows
    result['combined_summary'] = result['summary'] + summarize_controls(rows)
    result['original_three_condition_report_sha256'] = separation.pilot.sha(base_report)
    separation.write(output, result)
    return result


def summarize_controls(rows: list[dict]) -> list[dict]:
    # Reuse the same unchanged eligible-duration aggregation by mapping only the
    # presentation condition; native scores and timestamps are never altered.
    mapped = [{**row, 'condition': 'original'} for row in rows]
    return [{**row, 'condition': CONDITION} for row in separation.summarize(mapped) if row['condition'] == 'original']


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'infer', 'score'])
    parser.add_argument('--pack', type=Path, default=separation.OUTPUT)
    parser.add_argument('--protocol-sha256', required=True)
    parser.add_argument('--extension-sha256')
    parser.add_argument('--base-report', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(); pack = args.pack.resolve()
    if args.mode == 'prepare':
        result = prepare(pack, args.protocol_sha256)
    else:
        if not args.extension_sha256:
            parser.error('Use the hash frozen before new BTC inference')
        if args.mode == 'infer':
            result = infer(pack, args.protocol_sha256, args.extension_sha256)
        else:
            if not args.base_report or not args.output:
                parser.error('Scoring requires the saved original three-condition --base-report and fresh --output')
            result = score(pack, args.protocol_sha256, args.extension_sha256,
                           args.base_report.resolve(), args.output.resolve())
    print(json.dumps({k: result[k] for k in ('extension_sha256', 'failed_cases', 'runtime_seconds') if k in result}))
    if result.get('failed_cases'):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
