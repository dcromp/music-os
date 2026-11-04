"""Pinned neural pulse estimates for paired research WAVs; no player promotion."""
from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import time

import rhythm_grid as grid


def convert_native(beats, downbeats, duration: float) -> dict:
    raw_pulses = [float(value) for value in beats]
    raw_estimates = [float(value) for value in downbeats]
    if (not 2 <= len(raw_pulses) <= grid.MAX_BEATS
            or any(not grid._number(value) for value in raw_pulses)
            or any(a >= b for a, b in zip(raw_pulses, raw_pulses[1:]))):
        raise ValueError('Native beats must be finite ordered times')
    if any(not grid._number(value) for value in raw_estimates):
        raise ValueError('Native downbeat estimates must be finite')
    if any(a >= b for a, b in zip(raw_estimates, raw_estimates[1:])):
        raise ValueError('Native downbeat estimates must remain ordered')
    pulses = [value for value in raw_pulses if 0 <= value < duration]
    estimates = [value for value in raw_estimates if 0 <= value < duration]
    if len(pulses) < 2:
        raise ValueError('Fewer than two neural beats inside recording')
    intervals = sorted(b - a for a, b in zip(pulses, pulses[1:]))
    return {'beat_times_seconds': pulses, 'downbeat_times_seconds': estimates,
            'raw_beat_times_seconds': raw_pulses, 'raw_downbeat_times_seconds': raw_estimates,
            'outside_recording_beat_times_seconds': [value for value in raw_pulses if not 0 <= value < duration],
            'outside_recording_downbeat_times_seconds': [value for value in raw_estimates if not 0 <= value < duration],
            'pulse_bpm': 60 / intervals[len(intervals) // 2]}


def build(manifest_path: Path, config_path: Path, output: Path, checkpoint: Path) -> dict:
    import torch
    from beat_this.inference import File2Beats

    if importlib.metadata.version('beat-this') != '1.1.0' or torch.__version__ != '2.6.0':
        raise ValueError('Use pinned beat-this 1.1.0 / torch 2.6.0 environment')
    packet = grid.preflight(manifest_path, config_path, output)
    checkpoint_sha = grid.digest(checkpoint)
    if output.resolve() == checkpoint.resolve():
        raise ValueError('Output must not overwrite checkpoint')
    torch.set_num_threads(1)
    started = time.perf_counter()
    model = File2Beats(checkpoint_path=str(checkpoint), device='cpu', float16=False, dbn=False)
    load_seconds = time.perf_counter() - started
    result = {'schema_version': grid.SCHEMA, 'pack_id': packet['manifest'].get('pack_id'),
              'version': '0.1.1', 'status': 'estimated', 'gold': False,
              'manifest_sha256': packet['manifest_sha256'], 'config_sha256': packet['config_sha256'],
              'checkpoint_sha256': checkpoint_sha, 'model_load_seconds': load_seconds,
              'semantics': 'Native neural estimates preserved; bounded interface excludes outside-recording events and reports them separately as invalid native extras; no offset fitting, timing snapping or downbeat accuracy claim',
              'cases': []}
    for row in packet['rows']:
        case_started = time.perf_counter()
        beats, downbeats = model(str(row['audio']))
        native = convert_native(beats, downbeats, row['recording']['duration_seconds'])
        if grid.digest(row['audio']) != row['recording']['audio_sha256']:
            raise ValueError('Audio changed during inference')
        result['cases'].append({'recording': dict(row['recording']), **native,
            'beats_per_bar': None, 'meter_label': 'No verified downbeats/bar units', 'status': 'estimated',
            'analysis': {'id': 'beat-this-' + checkpoint.stem, 'library': 'beat-this', 'library_version': '1.1.0',
                         'runtime_seconds': time.perf_counter() - case_started,
                         'parameters': {'checkpoint': checkpoint.stem, 'checkpoint_sha256': checkpoint_sha,
                                        'device': 'cpu', 'threads': 1, 'float16': False, 'dbn': False,
                                        'tempo_guidance': False, 'source_separation': 'none'},
                         'downbeats_inferred': True, 'downbeat_accuracy_measured': False,
                         'score_is_calibrated_confidence': False, 'chord_boundaries_snapped': False}})
    if (grid.digest(manifest_path) != packet['manifest_sha256']
            or grid.digest(config_path) != packet['config_sha256']
            or grid.digest(checkpoint) != checkpoint_sha):
        raise ValueError('Frozen inputs/checkpoint changed during inference')
    for row in packet['rows']:
        if grid.digest(row['audio']) != row['recording']['audio_sha256']:
            raise ValueError('Input audio changed after inference')
    result['runtime_seconds'] = time.perf_counter() - started
    grid._publish(output, result, [*packet['protected'], checkpoint.resolve()], overwrite=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--checkpoint', type=Path, required=True)
    args = parser.parse_args()
    result = build(args.manifest.resolve(), args.config.resolve(), args.output.resolve(), args.checkpoint.resolve())
    print(json.dumps({'cases': len(result['cases']), 'runtime_seconds': result['runtime_seconds'],
                      'model_load_seconds': result['model_load_seconds'], 'output': str(args.output)}))


if __name__ == '__main__':
    main()
