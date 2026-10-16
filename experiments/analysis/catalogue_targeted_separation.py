"""Targeted Dylan G/Gm conflict investigation; no reference or default change."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import time
import numpy as np
import automatic_drafts as drafts
import catalogue_pitch_check as check
import curation
import separation_check as separation

ROOT = check.ROOT
CASE_ID = 'bob-dylan-knockin-heavens-door-youtube-20261011'
CONDITIONS = ('original-cache', 'resampling-control', 'minus-vocals', 'other')
TARGETED_SETTINGS = {
    'separator': {key: separation.SETTINGS[key] for key in ('model', 'device', 'threads', 'shifts', 'split', 'overlap', 'segment', 'jobs', 'dtype', 'sample_rate_hz', 'channels', 'normalization')},
    'resampling': 'exact mono22050 duplicated, julius22050->44100; native stereo mean then julius44100->22050; no trim/pad/offset',
    'conditions': {'original-cache': 'exact original PCM16 bytes', 'resampling-control': 'original roundtrip, no separation',
                   'minus-vocals': 'resampled original minus estimated vocals', 'other': 'estimated other mixture'},
    'storage': 'unscaled native stereo44100 and mono22050 IEEE FLOAT preserved; mono22050 PCM16 analysis copies',
    'pcm_encoding': 'one shared min(1,0.999/max_peak_across_all_new_mono_conditions) scale; round(value*scale*32768), reject clipping',
    'acoustic_evidence': 'existing spectral and frozen NNLS-Chroma; same feature coordinates within backend; own and matched active support',
    'btc_inference': False, 'automatic_corrections': False, 'default_change': False}


def prepare(baseline, output):
    baseline, output = baseline.resolve(strict=True), output.absolute()
    if not baseline.is_relative_to(ROOT) or not output.resolve().is_relative_to(ROOT) or output.exists() or output.is_symlink():
        raise ValueError('Use a new repository-local output')
    report = curation.read(baseline / 'report.json')
    if report.get('schema_version') != check.SCHEMA or report['module_sha256'] != drafts.digest(Path(check.__file__)):
        raise ValueError('Use the current source-paired baseline report')
    case = next(item for item in report['cases'] if item['id'] == CASE_ID)
    audio = check.DEFAULT_PACK / 'cases' / CASE_ID / 'audio.wav'
    drafts.verified_audio(audio, case['recording'])
    old = ROOT / 'experiments/generated/separation-check-v1'
    previous = curation.read(old / 'separation-report.json')['protocol_sha256']
    # Reuse existing official code/checkpoint/runtime checks before any new run.
    provenance = separation.validate_protocol(old, previous, require_runtime=True)
    output.mkdir(parents=True)
    protocol = {'schema_version': 'catalogue-targeted-separation-protocol-1.0',
                'frozen_before': 'Targeted separation; original BTC/CREMA and chroma diagnostics already exposed',
                'case_id': CASE_ID, 'recording': case['recording'],
                'audio': str(audio.relative_to(ROOT)), 'audio_sha256': drafts.digest(audio),
                'baseline_report': str((baseline / 'report.json').relative_to(ROOT)),
                'baseline_report_sha256': drafts.digest(baseline / 'report.json'),
                'previous_separator_protocol': str((old / 'protocol.json').relative_to(ROOT)),
                'previous_separator_protocol_sha256': previous,
                'checkpoint': provenance['checkpoint'], 'checkpoint_sha256': separation.MODEL_SHA,
                'settings': TARGETED_SETTINGS, 'conditions': list(CONDITIONS),
                'source_palette': case['source_shapes'],
                'cues': [item['native_event'] for item in case['retrospective_cue_audit']['btc']['cues']],
                'new_module_sha256': drafts.digest(Path(__file__)), 'palette_module_sha256': drafts.digest(Path(check.__file__)),
                'derivative_storage': 'native float WAV preserved; mono PCM16 analysis copies use one common non-clipping scale; no trimming or timestamp shift',
                'truth_available': False, 'accepted_arrangement': False,
                'limits': ['other is a residual mixture, not an isolated guitar stem',
                           'G/Gm cue timestamps are exposed BTC predictions, not physical chord boundaries',
                           'No accuracy, causal vocal-contamination or improved transcription conclusion follows from template scores']}
    separation.write(output / 'protocol.json', protocol)
    return drafts.digest(output / 'protocol.json')


def validate(pack, expected):
    pack = pack.resolve(strict=True)
    if not pack.is_relative_to(ROOT) or drafts.digest(pack / 'protocol.json') != expected:
        raise ValueError('Targeted protocol changed')
    protocol = curation.read(pack / 'protocol.json')
    if protocol['schema_version'] != 'catalogue-targeted-separation-protocol-1.0' or protocol['conditions'] != list(CONDITIONS) or protocol['settings'] != TARGETED_SETTINGS:
        raise ValueError('Unexpected targeted settings')
    for path, digest in ((ROOT / protocol['audio'], protocol['audio_sha256']),
                         (ROOT / protocol['baseline_report'], protocol['baseline_report_sha256']),
                         (Path(__file__), protocol['new_module_sha256']), (Path(check.__file__), protocol['palette_module_sha256'])):
        if drafts.digest(path) != digest: raise ValueError('Targeted source/code changed')
    previous = ROOT / protocol['previous_separator_protocol']
    separation.validate_protocol(previous.parent, protocol['previous_separator_protocol_sha256'], require_runtime=True)
    drafts.verified_audio(ROOT / protocol['audio'], protocol['recording'])
    return protocol


def paired_support(original, condition):
    if not np.array_equal(original['times'], condition['times']):
        raise ValueError('Conditions must have exactly the same feature centers')
    # Require nonzero active evidence in both, so a weaker stem cannot gain
    # apparent compatibility by dropping difficult frames from the denominator.
    silent = (original['silent'] | condition['silent'] |
              (np.linalg.norm(original['chroma'], axis=1) == 0) |
              (np.linalg.norm(condition['chroma'], axis=1) == 0))
    return {**original, 'silent': silent}, {**condition, 'silent': silent}


def chord_comparison(features, duration, first, last):
    major = check.score_window(features, ['G'], duration, first, last)
    minor = check.score_window(features, ['Gm'], duration, first, last)
    active = major['active_evidence_seconds']
    return {'active_evidence_seconds': active, 'G_cosine': major['proposed_zero_shift_cosine'],
            'Gm_cosine': minor['proposed_zero_shift_cosine'],
            'G_minus_Gm_cosine': major['proposed_zero_shift_cosine'] - minor['proposed_zero_shift_cosine'] if active else None}


def run(pack, expected):
    import demucs
    import torch
    import julius
    import soundfile as sf
    from demucs.apply import apply_model
    from demucs.hf import load_safetensors_model
    pack = pack.resolve(strict=True); protocol = validate(pack, expected)
    output = pack / 'outputs'
    if output.exists() or (pack / 'report.json').exists(): raise ValueError('Never overwrite a separation attempt')
    started = time.perf_counter(); torch.set_num_threads(1)
    mono, rate = sf.read(ROOT / protocol['audio'], dtype='float32')
    tensor = torch.from_numpy(mono).unsqueeze(0).expand(2, -1)
    wav = julius.resample_frac(tensor, rate, 44100)
    if wav.shape != (2, len(mono) * 2): raise ValueError('Input resampling changed duration')
    model = load_safetensors_model(ROOT / protocol['checkpoint']).eval()
    if model.sources != ['drums', 'bass', 'other', 'vocals'] or model.samplerate != 44100 or model.audio_channels != 2:
        raise ValueError('Unexpected model architecture')
    ref = wav.mean(0); mean = ref.mean(); std = ref.std() + 1e-8
    inference_started = time.perf_counter()
    with torch.inference_mode():
        native = apply_model(model, ((wav - mean) / std)[None], device='cpu', shifts=0,
                             split=True, overlap=.25, progress=False, num_workers=0, segment=None)[0] * std + mean
    inference_seconds = time.perf_counter() - inference_started
    print(f'Separated exact Dylan input in {inference_seconds:.1f}s', flush=True)
    origin = wav.numpy().T
    stems = {name: value.numpy().T for name, value in zip(model.sources, native)}
    separation.residuals(origin, stems)  # Shared shape/finite checks.
    variants = {'resampling-control': origin, 'minus-vocals': origin - stems['vocals'], 'other': stems['other']}
    mono_variants = {name: julius.resample_frac(torch.from_numpy(value.T.copy()).mean(0), 44100, rate).numpy() for name, value in variants.items()}
    if any(len(value) != len(mono) for value in mono_variants.values()): raise ValueError('Derivative frame count changed')
    peak = max(float(np.max(np.abs(value))) for value in mono_variants.values())
    scale = min(1.0, .999 / peak) if peak else 1.0
    output.mkdir()
    pins = {}
    for name, value in {**stems, 'minus-vocals': variants['minus-vocals'], 'resampled-origin': origin}.items():
        path = output / (name + '-native-float.wav'); sf.write(path, value, 44100, subtype='FLOAT')
        pins[path.name] = drafts.digest(path)
    source_copy = output / 'original-cache.wav'; shutil.copyfile(ROOT / protocol['audio'], source_copy)
    if drafts.digest(source_copy) != protocol['audio_sha256']: raise ValueError('Original cache copy changed')
    conversion = {}
    for name, value in mono_variants.items():
        if not np.all(np.isfinite(value)): raise ValueError('Nonfinite derivative')
        float_path = output / (name + '-mono-float.wav')
        sf.write(float_path, value, rate, subtype='FLOAT')
        reread, saved_rate = sf.read(float_path, dtype='float32')
        if saved_rate != rate or not np.array_equal(value, reread): raise ValueError('FLOAT derivative changed')
        pins[float_path.name] = drafts.digest(float_path)
        samples = np.rint(value * scale * 32768)
        if np.any(samples > 32767) or np.any(samples < -32768): raise ValueError('Derivative conversion would clip')
        sf.write(output / (name + '.wav'), samples.astype('<i2'), rate, subtype='PCM_16')
        decoded, saved_rate = sf.read(output / (name + '.wav'), dtype='float64')
        if saved_rate != rate or not np.array_equal(decoded, samples / 32768): raise ValueError('PCM analysis copy changed')
        conversion[name] = {'frames': len(value), 'pre_scale_peak_abs': float(np.max(np.abs(value))),
                            'common_scale': scale, 'clipped_samples': 0,
                            'quantization_error_rms': float(np.sqrt(np.mean((decoded - value.astype(float) * scale) ** 2))),
                            'max_quantization_error': float(np.max(np.abs(decoded - value.astype(float) * scale)))}
    all_features, conditions = {}, []
    duration = len(mono) / rate
    for name in CONDITIONS:
        audio = output / (name + '.wav'); signal, saved_rate = check.lab.read_wav(audio)
        if len(signal) != len(mono) or saved_rate != rate: raise ValueError('Saved analysis copy changed duration')
        evidence = check.nnls.extract(audio, CASE_ID + '--' + name)
        check.nnls.validate_evidence(evidence, audio)
        drafts.write_json(output / (name + '-nnls.json'), evidence)
        all_features[name] = {'spectral': check.features_from_spectral(audio), 'nnls': check.features_from_nnls(evidence)}
        pins[audio.name] = drafts.digest(audio); pins[name + '-nnls.json'] = drafts.digest(output / (name + '-nnls.json'))
        conditions.append({'condition': name, 'audio_sha256': pins[audio.name], 'amplitude': separation.amplitude(signal),
                           'full_palette': {method: check.score_window(features, protocol['source_palette'], duration) for method, features in all_features[name].items()}})
    cues = []
    for cue in protocol['cues']:
        first, last = cue['start_seconds'], cue['end_seconds']
        rows = []
        for condition in CONDITIONS:
            for method in ('spectral', 'nnls'):
                original, current = paired_support(all_features['original-cache'][method], all_features[condition][method])
                original_own = chord_comparison(all_features['original-cache'][method], duration, first, last)
                original_matched = chord_comparison(original, duration, first, last)
                rows.append({'condition': condition, 'method': method,
                             'own_support': chord_comparison(all_features[condition][method], duration, first, last),
                             'original_own_support': original_own,
                             'original_active_seconds_outside_matched_support': original_own['active_evidence_seconds'] - original_matched['active_evidence_seconds'],
                             'matched_original': original_matched,
                             'matched_condition': chord_comparison(current, duration, first, last)})
        cues.append({'native_btc_interval': cue, 'comparisons': rows})
    validate(pack, expected)
    report = {'schema_version': 'catalogue-targeted-separation-1.0', 'created_at_utc': datetime.now(timezone.utc).isoformat(),
              'protocol_sha256': expected, 'model_inference_seconds': inference_seconds,
              'runtime_seconds': time.perf_counter() - started, 'runtime': separation.pinned_runtime(),
              'common_pcm_scale': scale, 'pcm_conversion': conversion,
              'conditions': conditions, 'cue_comparisons': cues, 'output_hashes': pins,
              'accepted_arrangement': False, 'accuracy_score': None, 'raw_source_audio_modified': False,
              'default_workflow_changed': False, 'human_correction_seconds': None,
              'limits': protocol['limits'] + ['Scores use full-mix/source estimates, not a performed chord reference.',
                  'Matched-support scores exclude inactive/zero evidence in either condition; report coverage separately.',
                  'Research outputs do not replace the original learner audio or charts.']}
    separation.write(pack / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--baseline', type=Path, required=True); p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--pack', type=Path, required=True); p.add_argument('--expected', required=True)
    args = parser.parse_args()
    if args.command == 'prepare': print(json.dumps({'protocol_sha256': prepare(args.baseline, args.output)}))
    else:
        report = run(args.pack, args.expected)
        print(json.dumps({'runtime_seconds': report['runtime_seconds'], 'default_workflow_changed': False}))
