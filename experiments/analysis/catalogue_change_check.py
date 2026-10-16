"""Exact-recording native change and sustained-harmony inspection for the catalogue.

This inventories existing predictions; it neither refines timestamps nor treats
model agreement as physical timing truth. Riff notes are never inferred here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import shutil
import tempfile
import time

import automatic_drafts as drafts
import catalogue_timing_review as timing
import curation

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PACK = ROOT / 'experiments/generated/catalogue-curation-20261014'
SCHEMA = 'catalogue-change-check-1.0'
# Retrospective source-guided review targets, never section or accuracy labels.
TARGETS = {
    'wild-thing': [('A', 6)],
    'love-me-do': [('C', 5), ('D', 1)],
    'knockin-on-heaven-s-door': [('Am', 2), ('C', 2)],
    'brown-eyed-girl': [('Em', 1), ('D', 3)],
    'twist-and-shout': [('A', 6)],
    'seven-nation-army': [],
    'come-as-you-are': [],
    'creep': [('B', 2), ('Cm', 2)],
    'the-house-of-the-rising-sun': [('Dm', 1)],
    'wonderwall': [('F#m', 2), ('D', 2)],
}


def case_review(first, second, review):
    context = review['source_context']
    song = context['song_id']
    if song not in TARGETS:
        raise ValueError('Declare source-guided targets for this song')
    # These two tracks have no entry chord palette: do not promote chord spans
    # into a purported riff, note sequence or physical phrase map.
    riff_first = context['entry_shapes'] is None
    if riff_first and TARGETS[song]:
        raise ValueError('Riff-first songs must not acquire triad hold targets')
    rows = []
    for model, chart in (('btc', first), ('crema', second)):
        for span in timing.core_timeline(chart):
            for label, minimum in TARGETS[song]:
                if span['key'] == timing.key_for(label) and span['end_seconds'] - span['start_seconds'] >= minimum:
                    rows.append({'model': model, 'target': label, 'native_span': span,
                                 'accepted_section': False})
    return {'recording': first['recording'], 'song_id': song, 'riff_first': riff_first,
            'boundary_review': timing.boundary_review(first, second),
            'fixed_coverage_samples': [p for p in review['points'] if p['kind'] == 'coverage-sample'],
            'source_guided_hold_candidates': rows,
            'semantics': 'Directed native chord-label changes and harmonic hold candidates only. Riff-first labels do not establish riff notes or phrase timing. No attacks, bar counts, formal sections or physical changes are accepted.',
            'accepted_arrangement': False, 'physical_timing_accuracy': None}


def run(pack, output, *, root=ROOT):
    root = root.resolve(); pack = pack.resolve(strict=True); output = output.absolute()
    destination = output.resolve()
    generated = root / 'experiments/generated'
    if (not pack.is_relative_to(generated) or not destination.is_relative_to(generated)
            or output.exists() or output.is_symlink() or destination.is_relative_to(pack)
            or pack.is_relative_to(destination)):
        raise ValueError('Use an unused generated output, separate from the input pack')
    files, manifest = curation.public_files(pack)
    sources = {path: drafts.digest(path) for path in files.values()}
    dependencies = (Path(__file__), Path(timing.__file__), Path(curation.__file__),
                    Path(curation.review_pack.__file__), Path(drafts.__file__),
                    Path(timing.lab.__file__), Path(timing.core_chord_screen.__file__),
                    Path(timing.pitch.rich_quality_suite.__file__))
    sources.update({p: drafts.digest(p) for p in dependencies})
    private = pack / 'private-drafts'
    if private.is_symlink():
        raise ValueError('Do not follow private draft aliases')
    saved = set(private.glob('*.json'))
    if any(path.is_symlink() for path in saved):
        raise ValueError('Do not follow private draft aliases')
    sources.update({p: drafts.digest(p) for p in saved})
    rows = []; started = time.perf_counter()
    for case in manifest['cases']:
        folder = pack / 'cases' / case['id']
        first, second, review = (curation.read(folder / f) for f in ('primary.json', 'crema.json', 'review.json'))
        row = case_review(first, second, review)
        rows.append({'id': case['id'], 'title': case['name'], 'native_artifacts': case['artifacts'], **row})
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.change-check-', dir=output.parent))
    try:
        for row in rows:
            drafts.write_json(staging / (row['id'] + '.json'), row)
        if (private.is_symlink() or set(private.glob('*.json')) != saved
                or any(not p.is_file() or drafts.digest(p) != sha for p, sha in sources.items())):
            raise ValueError('An input or saved draft changed during inspection')
        result = {'schema_version': SCHEMA, 'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'status': 'retrospective native timing/contrast inspection; no acceptance', 'gold': False,
                  'policy': timing.POLICY, 'source_guided_targets': TARGETS,
                  'source_sha256': {str(p.relative_to(root)): sha for p, sha in sources.items()},
                  'runtime_seconds': time.perf_counter() - started, 'cases': rows,
                  'raw_inputs_modified': False, 'private_drafts_modified': False,
                  'accepted_arrangements': 0, 'human_correction_seconds': None}
        drafts.write_json(staging / 'report.json', result)
        staging.rename(output)
        return result
    except Exception:
        shutil.rmtree(staging)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack', type=Path, default=DEFAULT_PACK)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.pack, args.output)
    print({'cases': len(result['cases']), 'runtime_seconds': result['runtime_seconds']})
