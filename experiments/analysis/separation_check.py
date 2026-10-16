"""Retrospective paired Demucs residual/BTC research; no playback acceptance."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import resource
import shutil
import subprocess
import sys
import time

import numpy as np

import guitarset_pilot as pilot
import jazzsamba_check as jazz
import lab

ROOT = lab.ROOT
SOURCE = lab.GENERATED / 'jazzsamba-reference-v1'
OUTPUT = lab.GENERATED / 'separation-check-v1'
ASSETS = ROOT / 'experiments/candidate-assets/demucs-4.1.0'
CODE_COMMIT = '6a604bb002d12c4fbabb303ba64db40b5c5743f0'
MODEL_REVISION = 'cbc8a9b1a87023b7fd74e7b3412e6321c0eab003'
MODEL_SHA = 'd9fa14133cfcc034a6758923bb3a8ca9f8dfd0b582134643bbf83f72c17576dd'
CONDITIONS = ('original', 'minus-drums', 'minus-drums-vocals')
SETTINGS = {'model': '955717e8', 'device': 'cpu', 'threads': 1, 'shifts': 0,
            'split': True, 'overlap': .25, 'segment': None, 'jobs': 0,
            'dtype': 'float32', 'sample_rate_hz': 44100, 'channels': 2,
            'btc_threads': 4, 'btc_smoothing': 'unchanged native adapter / none',
            'normalization': 'ref=mean(stereo channels); mean=ref.mean; std=ref.std(unbiased=True)+1e-8; (wav-mean)/std; each native source restored by source*std+mean',
            'residuals': {'minus-drums': 'original_resampled_stereo - estimated_drums',
                          'minus-drums-vocals': 'original_resampled_stereo - estimated_drums - estimated_vocals'},
            'resampling': 'julius.resample_frac 22050->44100, mono duplicated; residual stereo mean then julius.resample_frac 44100->22050; no trim/pad/offset/endpoint scaling',
            'storage': 'native stereo and detector-input mono IEEE float32 WAV; no clipping, limiting, gain normalization or lossy codec'}
KINDS = ('supported-rich-Harte', 'declared-major-minor-triad-projection')


def read(path: Path) -> dict:
    return json.loads(path.read_text())


def write(path: Path, packet: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(packet, stream, indent=2, allow_nan=False)
        stream.write('\n')


def confined(base: Path, relative: str) -> Path:
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('Expected a confined relative path')
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError('Path escapes paired research pack')
    return path


def pinned_runtime() -> dict:
    return {'python': platform.python_version(), 'machine': platform.machine(),
            'platform': platform.platform(), 'packages': dict(sorted(
                (d.metadata['Name'].lower(), d.version) for d in importlib.metadata.distributions()))}


def amplitude(samples) -> dict:
    array = np.asarray(samples, dtype=np.float64)
    if array.ndim not in (1, 2) or not array.size or not np.isfinite(array).all():
        raise ValueError('Audio must contain nonempty finite mono/stereo samples')
    return {'frames': len(array), 'channels': 1 if array.ndim == 1 else array.shape[1],
            'rms': float(np.sqrt(np.mean(array ** 2))), 'peak_abs': float(np.max(np.abs(array))),
            'dc_mean': float(array.mean()), 'samples_above_unit_fraction': float(np.mean(np.abs(array) > 1)),
            'first_difference_rms': float(np.sqrt(np.mean(np.diff(array, axis=0) ** 2))) if len(array) > 1 else 0.0}


def residuals(original, stems: dict) -> dict:
    original = np.asarray(original)
    amplitude(original)
    if set(stems) != {'drums', 'bass', 'other', 'vocals'}:
        raise ValueError('Standard HTDemucs requires exactly four native stems')
    for value in stems.values():
        if np.asarray(value).shape != original.shape:
            raise ValueError('Separation changed native frame/channel dimensions')
        amplitude(value)
    return {'minus-drums': original - stems['drums'],
            'minus-drums-vocals': original - stems['drums'] - stems['vocals']}


def validate_protocol(pack: Path, expected: str, require_runtime: bool = False) -> dict:
    path = pack / 'protocol.json'
    if pilot.sha(path) != expected:
        raise ValueError('Frozen protocol hash mismatch')
    protocol = read(path)
    if protocol['conditions'] != list(CONDITIONS) or protocol['settings'] != SETTINGS:
        raise ValueError('Frozen conditions/settings differ')
    for relative, digest in protocol['frozen_source_files'].items():
        if pilot.sha(confined(ROOT, relative)) != digest:
            raise ValueError('Frozen source changed: ' + relative)
    for case in protocol['cases']:
        for key, digest_key in (('audio', 'audio_sha256'), ('reference', 'reference_sha256'),
                                ('core_reference', 'core_reference_sha256'), ('cached_btc', 'cached_btc_sha256')):
            if pilot.sha(confined(pack, case[key])) != case[digest_key]:
                raise ValueError('Frozen input/reference/control changed: ' + case['id'])
    if require_runtime:
        import demucs
        if pinned_runtime() != protocol['separator_runtime']:
            raise ValueError('Separator runtime changed')
        source_pins = protocol['model_source_pins']
        installed = Path(demucs.__file__).parent
        for name, digest in protocol['separator_module_sha256'].items():
            if pilot.sha(installed / name) != digest:
                raise ValueError('Frozen installed separator module changed')
        for name, pin in source_pins['official_files'].items():
            if name.endswith('.py') and pilot.sha(installed / name) != pin['sha256']:
                raise ValueError('Installed Demucs differs from pinned author source')
        checkpoint = confined(ROOT, protocol['checkpoint'])
        if checkpoint.stat().st_size != 84025440 or pilot.sha(checkpoint) != MODEL_SHA:
            raise ValueError('Official safetensors checkpoint mismatch')
    return protocol


def prepare(source: Path, output: Path, assets: Path) -> dict:
    import soundfile as sf
    import demucs
    if output.exists() or output.is_relative_to(source):
        raise ValueError('Choose a fresh output outside the source pack')
    pins = read(assets / 'source-pins.json')
    if (demucs.__version__ != '4.1.0' or pins['code_commit'] != CODE_COMMIT
            or pins['model_revision'] != MODEL_REVISION or pins['checkpoint']['sha256'] != MODEL_SHA):
        raise ValueError('Unexpected official code/model provenance')
    checkpoint = assets / '955717e8.safetensors'
    if checkpoint.stat().st_size != 84025440 or pilot.sha(checkpoint) != MODEL_SHA:
        raise ValueError('Checkpoint size/hash mismatch')
    for name, pin in pins['official_files'].items():
        if pilot.sha(assets / name) != pin['sha256']:
            raise ValueError('Official source asset changed')
        if name.endswith('.py') and pilot.sha(Path(demucs.__file__).parent / name) != pin['sha256']:
            raise ValueError('Installed Demucs differs from official tagged source')
    manifest = read(source / 'manifest.json')
    original_protocol = read(source / 'chord-extension-protocol.json')
    if pilot.sha(source / 'manifest.json') != original_protocol['manifest_sha256']:
        raise ValueError('Original paired source manifest changed')
    output.mkdir(parents=True)
    cases = []
    for case in manifest['cases']:
        folder = output / 'cases' / case['id']; folder.mkdir(parents=True)
        audio = confined(source, case['audio']); info = sf.info(audio)
        if (pilot.sha(audio) != case['source']['prepared_audio_sha256']
                or info.frames != 1323000 or info.samplerate != 22050 or info.channels != 1):
            raise ValueError('Expected exact first60 mono 22050 Hz prepared input')
        row = {'id': case['id'], 'original_split': case['split'],
               'evaluation_role': 'retrospective diagnostic; previous scores exposed',
               'duration_seconds': 60.0, 'sample_rate_hz': 22050, 'frames': info.frames}
        for name, source_path in [('audio', audio), ('reference', confined(source, case['reference'])),
                                  ('core_reference', confined(source, case['core_reference'])),
                                  ('cached_btc', source / 'cases' / case['id'] / 'btc.json')]:
            destination = folder / {'audio': 'audio.wav', 'reference': 'intended.json',
                                    'core_reference': 'core.json', 'cached_btc': 'original-btc.json'}[name]
            shutil.copyfile(source_path, destination)
            row[name] = str(destination.relative_to(output)); row[name + '_sha256'] = pilot.sha(destination)
        # Original cached prediction is an untouched four-thread BTC control.
        control = read(output / row['cached_btc'])
        if (control['recording']['audio_sha256'] != row['audio_sha256']
                or control['recording']['id'] != row['id']
                or control['analysis']['parameters']['threads'] != SETTINGS['btc_threads']):
            raise ValueError('Original BTC control identity/settings mismatch')
        cases.append(row)
    if len(cases) != 3:
        raise ValueError('Bounded comparison requires exactly the existing three excerpts')
    source_files = ['experiments/analysis/separation_check.py', 'experiments/analysis/jazzsamba_check.py',
                    'experiments/analysis/guitarset_validation.py', 'experiments/analysis/guitarset_pilot.py',
                    'experiments/analysis/lab.py', 'experiments/analysis/candidates/btc_adapter.py',
                    'experiments/analysis/requirements-demucs.txt']
    btc_repo = ROOT / 'experiments/candidate-assets/btc-ismir19'
    for path in sorted(btc_repo.rglob('*.py')):
        source_files.append(str(path.relative_to(ROOT)))
    for name in ('run_config.yaml', 'test/btc_model.pt'):
        source_files.append(str((btc_repo / name).relative_to(ROOT)))
    # Snapshot BTC's existing isolated runtime without loading either model.
    code = 'import importlib.metadata,platform,json;print(json.dumps({"python":platform.python_version(),"machine":platform.machine(),"platform":platform.platform(),"packages":dict(sorted((d.metadata["Name"].lower(),d.version) for d in importlib.metadata.distributions()))}))'
    btc_runtime = json.loads(subprocess.check_output([str(ROOT / '.venv-btc/bin/python'), '-c', code], text=True))
    protocol = {'schema_version': 'separation-research-protocol-1.0', 'date': '2026-10-12',
                'frozen_before': 'All separation and derivative BTC inference; prior original mixture chord results exposed',
                'selection': 'All three existing JazzSAMBA first60 excerpts; BTC selected retrospectively because it led the exposed mixture benchmark',
                'accepted_for_playback': False, 'conditions': list(CONDITIONS), 'settings': SETTINGS,
                'reference_conditions': list(KINDS), 'model_source_pins': pins,
                'checkpoint': str(checkpoint.relative_to(ROOT)),
                'source_pack': str(source.relative_to(ROOT)), 'source_manifest_sha256': pilot.sha(source / 'manifest.json'),
                'source_selection_sha256': pilot.sha(source / 'selection.json'),
                'separator_runtime': pinned_runtime(), 'btc_runtime': btc_runtime,
                'separator_module_sha256': {str(p.relative_to(Path(demucs.__file__).parent)): pilot.sha(p)
                    for p in sorted(Path(demucs.__file__).parent.rglob('*.py'))},
                'separator_runtime_sha256': hashlib.sha256(json.dumps(pinned_runtime(), sort_keys=True).encode()).hexdigest(),
                'btc_runtime_sha256': hashlib.sha256(json.dumps(btc_runtime, sort_keys=True).encode()).hexdigest(),
                'frozen_source_files': {name: pilot.sha(ROOT / name) for name in source_files}, 'cases': cases,
                'metrics': 'Duration-weighted unchanged mir_eval0.8.2 root/majmin with explicit eligible coverage; no physical-attack claim; amplitude/reconstruction diagnostics describe signal changes, not perceptual quality or separation SDR',
                'limitations': ['Instrumental jazz piano/bass/drums/horn mixtures, no guitar/vocals; no guitar-isolation claim.',
                                'Written chart grids are not note-level performed-harmony or physical-attack truth.',
                                'No threshold/model/condition tuning; prior experiment holdouts already exposed.',
                                'Code MIT; model weights commercial terms unresolved; dataset reuse terms unresolved; local research only.']}
    write(output / 'protocol.json', protocol)
    return {'protocol_sha256': pilot.sha(output / 'protocol.json'), 'cases': len(cases)}


def separate(pack: Path, expected: str) -> dict:
    import soundfile as sf
    import torch
    import julius
    from demucs.apply import apply_model
    from demucs.hf import load_safetensors_model
    protocol = validate_protocol(pack, expected, require_runtime=True)
    report_path = pack / 'separation-report.json'
    if report_path.exists():
        raise ValueError('Saved separation attempt exists; choose a fresh pack')
    torch.set_num_threads(1)
    started = time.perf_counter()
    model = load_safetensors_model(ROOT / protocol['checkpoint']).eval()
    if (model.sources != ['drums', 'bass', 'other', 'vocals'] or model.samplerate != 44100
            or model.audio_channels != 2 or float(model.segment) != 7.8):
        raise ValueError('Unexpected native model architecture')
    model_load = time.perf_counter() - started
    results, inference_cases = [], []
    for case in protocol['cases']:
        timer = time.perf_counter(); folder = pack / 'cases' / case['id']
        row = {'id': case['id'], 'status': 'error', 'accepted_for_playback': False}
        try:
            mono, rate = sf.read(pack / case['audio'], dtype='float32')
            tensor = torch.from_numpy(mono).unsqueeze(0).expand(2, -1)
            wav = julius.resample_frac(tensor, rate, model.samplerate)
            if wav.shape != (2, case['frames'] * 2):
                raise ValueError('Resampling changed source duration')
            ref = wav.mean(0); mean = ref.mean(); std = ref.std() + 1e-8
            inference_started = time.perf_counter()
            with torch.inference_mode():
                native = apply_model(model, ((wav - mean) / std)[None], device='cpu',
                                     shifts=0, split=True, overlap=.25, progress=False,
                                     num_workers=0, segment=None)[0] * std + mean
            inference_seconds = time.perf_counter() - inference_started
            origin = wav.numpy().T
            stems = {name: value.numpy().T for name, value in zip(model.sources, native)}
            variants = residuals(origin, stems)
            native_pins, diagnostics = {}, {}
            for name, samples in {**stems, **variants}.items():
                path = folder / (name + '-native.wav')
                if path.exists():
                    raise ValueError('Refusing to replace saved native audio')
                sf.write(path, samples, 44100, subtype='FLOAT')
                native_pins[name] = {'path': str(path.relative_to(pack)), 'sha256': pilot.sha(path)}
                diagnostics[name] = amplitude(samples)
            for condition, samples in variants.items():
                target = julius.resample_frac(torch.from_numpy(samples.T.copy()).mean(0), 44100, rate).numpy()
                if len(target) != case['frames']:
                    raise ValueError('Residual input frame count changed; no truncation/padding allowed')
                audio = folder / (condition + '.wav')
                if audio.exists():
                    raise ValueError('Refusing to replace saved detector input')
                sf.write(audio, target, rate, subtype='FLOAT')
                reread, saved_rate = sf.read(audio, dtype='float32')
                if saved_rate != rate or not np.array_equal(target, reread):
                    raise ValueError('Float WAV publication changed samples')
                inference_cases.append({'id': case['id'], 'condition': condition,
                                        'audio': str(audio.relative_to(pack)), 'audio_sha256': pilot.sha(audio),
                                        'source_audio_sha256': case['audio_sha256'], 'frames': len(target),
                                        'sample_rate_hz': rate, 'duration_seconds': len(target) / rate})
                diagnostics[condition + '-detector-input'] = amplitude(target)
            reconstruction = sum(stems.values()) - origin
            row.update(status='ok', model_inference_seconds=inference_seconds,
                       total_separation_seconds=time.perf_counter() - timer,
                       original_native_diagnostics=amplitude(origin), native_output_pins=native_pins,
                       output_diagnostics=diagnostics, reconstruction_error_diagnostics=amplitude(reconstruction),
                       reconstruction_error_rms_ratio=(amplitude(reconstruction)['rms'] / amplitude(origin)['rms']),
                       restored_dc_mean=float(mean), restored_standard_deviation=float(std))
            print(f"Demucs {case['id']}: {row['total_separation_seconds']:.3f}s", flush=True)
        except Exception as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
            print(f"Demucs {case['id']}: FAILED {row['error']}", flush=True)
        results.append(row)
    report = {'schema_version': 'separation-attempt-1.0', 'protocol_sha256': expected,
              'model_load_seconds': model_load, 'runtime_seconds': time.perf_counter() - started,
              'process_peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024),
              'failed_cases': sum(r['status'] != 'ok' for r in results), 'cases': results,
              'accepted_for_playback': False}
    write(report_path, report)
    write(pack / 'inference-inputs.json', {'protocol_sha256': expected,
          'frozen_before': 'All derivative BTC inference', 'separation_report_sha256': pilot.sha(report_path),
          'cases': inference_cases, 'accepted_for_playback': False})
    validate_protocol(pack, expected, require_runtime=True)
    return report


def infer(pack: Path, expected: str) -> dict:
    from candidates import btc_adapter
    protocol = validate_protocol(pack, expected)
    if pinned_runtime() != protocol['btc_runtime']:
        raise ValueError('BTC runtime changed')
    inputs_path = pack / 'inference-inputs.json'; inputs = read(inputs_path)
    if (inputs['protocol_sha256'] != expected
            or inputs['separation_report_sha256'] != pilot.sha(pack / 'separation-report.json')):
        raise ValueError('Derivative input declaration/separation pairing mismatch')
    declaration_sha = pilot.sha(inputs_path)
    if (pack / 'btc-attempt.json').exists():
        raise ValueError('Saved BTC attempt exists; choose a fresh pack')
    rows = []; started = time.perf_counter()
    for case in inputs['cases']:
        row = {'id': case['id'], 'condition': case['condition'], 'status': 'error'}
        try:
            path = confined(pack, case['audio'])
            if pilot.sha(path) != case['audio_sha256']:
                raise ValueError('Declared derivative audio changed before inference')
            result = btc_adapter.infer(path, case['id'], ROOT / 'experiments/candidate-assets/btc-ismir19', 4)
            result['analysis']['source_separation'] = {'condition': case['condition'],
                  'protocol_sha256': expected, 'inference_inputs_sha256': declaration_sha,
                  'source_audio_sha256': case['source_audio_sha256'], 'accepted_for_playback': False}
            target = pack / 'cases' / case['id'] / (case['condition'] + '-btc.json')
            write(target, result)
            row.update(status='ok', prediction=str(target.relative_to(pack)), prediction_sha256=pilot.sha(target),
                       inference_seconds=result['analysis']['runtime_seconds'])
            print(f"BTC {case['id']} / {case['condition']}: {row['inference_seconds']:.3f}s", flush=True)
        except Exception as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
            print(f"BTC {case['id']} / {case['condition']}: FAILED {row['error']}", flush=True)
        rows.append(row)
    if declaration_sha != pilot.sha(inputs_path):
        raise ValueError('Inference input declaration changed during batch')
    report = {'schema_version': 'separated-btc-attempt-1.0', 'protocol_sha256': expected,
              'inference_inputs_sha256': declaration_sha, 'runtime_seconds': time.perf_counter() - started,
              'cases': rows, 'failed_cases': sum(r['status'] != 'ok' for r in rows), 'accepted_for_playback': False}
    write(pack / 'btc-attempt.json', report)
    validate_protocol(pack, expected)
    return report


def validate_derivative(reference: dict, prediction: dict, source: dict, derivative: dict, expected: str, declaration_sha: str) -> None:
    recording = prediction['recording']; native = reference['recording']
    for key, value in (('id', source['id']), ('audio_sha256', source['audio_sha256']),
                       ('sample_rate_hz', source['sample_rate_hz']), ('duration_seconds', source['duration_seconds'])):
        if native.get(key) != value:
            raise ValueError('Reference differs from original paired source: ' + key)
    for key in ('id', 'sample_rate_hz', 'duration_seconds', 'audio_sha256'):
        if recording.get(key) != derivative.get(key):
            raise ValueError('Prediction differs from declared derivative: ' + key)
    if derivative['source_audio_sha256'] != source['audio_sha256'] or derivative['frames'] != source['frames']:
        raise ValueError('Derivative lost original source identity/frame count')
    lineage = prediction['analysis']['source_separation']
    if lineage != {'condition': derivative['condition'], 'protocol_sha256': expected,
                   'inference_inputs_sha256': declaration_sha,
                   'source_audio_sha256': source['audio_sha256'], 'accepted_for_playback': False}:
        raise ValueError('Prediction derivative provenance differs')


def summarize(rows: list[dict]) -> list[dict]:
    summaries = []
    for kind in KINDS:
        for condition in CONDITIONS:
            requested = [r for r in rows if r['reference_kind'] == kind and r['condition'] == condition]
            good = [r for r in requested if r['status'] == 'ok']
            duration = sum(r['duration_seconds'] for r in good)
            summary = {'reference_kind': kind, 'condition': condition, 'requested_cases': len(requested),
                       'successful_cases': len(good), 'failed_cases': len(requested) - len(good),
                       'requested_audio_seconds': 60 * len(requested), 'scored_audio_seconds': duration,
                       'scored_audio_coverage': duration / (60 * len(requested)) if requested else 0}
            for metric in ('root', 'majmin', 'root_chord_only', 'majmin_chord_only'):
                eligible = sum(r[metric + '_eligible_seconds'] for r in good)
                summary[metric] = sum((r[metric] or 0) * r[metric + '_eligible_seconds'] for r in good) / eligible if eligible else None
                summary[metric + '_eligible_seconds'] = eligible
                summary[metric + '_reference_coverage'] = eligible / duration if duration else None
            summary['estimated_unknown_seconds'] = sum(r['estimated_unknown_seconds'] for r in good)
            summary['detector_seconds'] = sum(r['analysis_runtime_seconds'] for r in good)
            summary['separation_seconds'] = sum(r['separation_seconds'] for r in good)
            summaries.append(summary)
    return summaries


def score(pack: Path, expected: str, output: Path) -> dict:
    import mir_eval
    if mir_eval.__version__ != '0.8.2' or output.exists():
        raise ValueError('Use mir_eval0.8.2 and a fresh report path')
    protocol = validate_protocol(pack, expected)
    separation_path = pack / 'separation-report.json'; separation = read(separation_path)
    attempts_path = pack / 'btc-attempt.json'; attempts = read(attempts_path)
    inputs_path = pack / 'inference-inputs.json'; inputs = read(inputs_path); input_sha = pilot.sha(inputs_path)
    if (separation['protocol_sha256'] != expected or attempts['protocol_sha256'] != expected
            or inputs['protocol_sha256'] != expected or attempts['inference_inputs_sha256'] != input_sha
            or inputs['separation_report_sha256'] != pilot.sha(separation_path)):
        raise ValueError('Saved attempt/declaration hashes differ')
    derivatives = {(r['id'], r['condition']): r for r in inputs['cases']}
    predictions = {(r['id'], r['condition']): r for r in attempts['cases']}
    separations = {r['id']: r for r in separation['cases']}
    rows = []
    for case in protocol['cases']:
        rich = lab.load_chart(pack / case['reference']); core = lab.load_chart(pack / case['core_reference'])
        jazz.validate_core_reference(rich, core)
        for kind, reference in zip(KINDS, (rich, core)):
            reference = jazz.harte_reference(reference)
            for condition in CONDITIONS:
                row = {'id': case['id'], 'reference_kind': kind, 'condition': condition,
                       'status': 'error', 'accepted_for_playback': False}
                try:
                    if condition == 'original':
                        prediction_path = pack / case['cached_btc']; prediction = lab.load_chart(prediction_path)
                        row.update(jazz.checked_score(reference, prediction, 'btc'), separation_seconds=0, cached_control=True)
                    else:
                        key = case['id'], condition; derivative = derivatives[key]; attempt = predictions[key]
                        if attempt['status'] != 'ok' or separations[case['id']]['status'] != 'ok':
                            raise ValueError('Separation or detector failed; retained in saved attempt')
                        if pilot.sha(confined(pack, derivative['audio'])) != derivative['audio_sha256']:
                            raise ValueError('Derivative audio changed after inference')
                        prediction_path = confined(pack, attempt['prediction'])
                        if pilot.sha(prediction_path) != attempt['prediction_sha256']:
                            raise ValueError('Saved derivative prediction changed')
                        prediction = lab.load_chart(prediction_path)
                        validate_derivative(reference, prediction, case, derivative, expected, input_sha)
                        # Gold remains byte-identical and is never rebound to a derivative hash.
                        # Source/derivative lineage is checked above before unchanged native scoring.
                        row.update(pilot.score(reference, prediction, 'btc'),
                                   separation_seconds=separations[case['id']]['total_separation_seconds'], cached_control=False)
                    row.update(status='ok', prediction_sha256=pilot.sha(prediction_path),
                               analysis_provenance=prediction['analysis'])
                except Exception as error:
                    row['error'] = type(error).__name__ + ': ' + str(error)
                rows.append(row)
    result = {'schema_version': 'separation-check-1.0', 'date': '2026-10-12', 'protocol': protocol,
              'protocol_sha256': expected, 'inference_inputs_sha256': input_sha,
              'separation_report_sha256': pilot.sha(separation_path), 'btc_attempt_sha256': pilot.sha(attempts_path),
              'summary': summarize(rows), 'cases': rows, 'separation': separation,
              'btc_batch_seconds': attempts['runtime_seconds'], 'accepted_for_playback': False,
              'runtime_note': 'Both residual conditions share one separation per source; condition totals intentionally include that same one-time cost and must not be added together. Original inference times are cached historical CPU4 runs; new BTC also CPU4. CPU1 applies to separator.',
              'limitations': protocol['limitations']}
    write(output, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['prepare', 'separate', 'infer', 'score'])
    parser.add_argument('--source-pack', type=Path, default=SOURCE)
    parser.add_argument('--pack', type=Path, default=OUTPUT)
    parser.add_argument('--assets', type=Path, default=ASSETS)
    parser.add_argument('--protocol-sha256')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.mode == 'prepare':
        result = prepare(args.source_pack.resolve(), args.pack.resolve(), args.assets.resolve())
    else:
        if not args.protocol_sha256:
            parser.error('A declared --protocol-sha256 is required')
        if args.mode == 'score':
            if not args.output:
                parser.error('Scoring needs a fresh --output')
            result = score(args.pack.resolve(), args.protocol_sha256, args.output.resolve())
        else:
            result = globals()[args.mode](args.pack.resolve(), args.protocol_sha256)
    print(json.dumps(result.get('summary', {k: result[k] for k in ('protocol_sha256', 'failed_cases', 'runtime_seconds') if k in result}), indent=2))
    cases = result.get('cases', [])
    if result.get('failed_cases') or (isinstance(cases, list) and any(r['status'] != 'ok' for r in cases)):
        raise SystemExit(2)


if __name__ == '__main__':
    main()
