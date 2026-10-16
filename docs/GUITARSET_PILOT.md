# GuitarSet real-guitar diagnostic pilot

10 October 2026. **Six preselected acoustic-guitar microphone comping performances × five raw algorithms: 30 successful model runs, 60 reference comparisons.** The recordings total 182.36 seconds. This is a small diagnostic pilot, not an app accuracy estimate or final model selection.

## Results

Scores are `mir_eval 0.8.2` duration-weighted agreement, aggregated over the eligible reference duration. Roots and major/minor quality are separate questions. The reference labels contain no `N` silence spans; chord-only scores are also retained in the JSON to make that explicit.

| Candidate | Root | Intended major/minor | Performed major/minor |
|---|---:|---:|---:|
| Baseline | 58.9% | 54.3% | 59.0% |
| BTC | 83.8% | 84.0% | 88.4% |
| CREMA | **94.4%** | **93.9%** | **92.7%** |
| ChordMini | 79.4% | 79.5% | 81.2% |
| Chordino | 88.7% | 82.7% | 88.5% |

Root coverage is effectively 100%. Major/minor coverage is **98.1% for intended labels and 78.4% for performed labels**. `mir_eval.majmin` excludes references outside its major/minor/no-chord gamut, including power chords, suspensions and incompatible altered triads. It retains extensions that preserve the relevant triad. A high performed score therefore does not mean the algorithm has correctly transcribed every performed chord. The two major/minor columns have different denominators and should not be interpreted as a before/after improvement.

The root scores for intended and performed references are identical because GuitarSet inherits performed roots from the instructed lead sheet. They are one root test, not two independent validations.

## What changed our interpretation

CREMA, the weakest of the pretrained candidates on the procedural synthetic suite, leads this small real-guitar pilot. ChordMini's synthetic lead did not transfer to these performances. Synthetic tests remain useful for controlled failure diagnosis; they are insufficient for ranking production candidates.

| Performance | Baseline | BTC | CREMA | ChordMini | Chordino |
|---|---:|---:|---:|---:|---:|
| 00 · Singer-songwriter · 84 BPM | 58.4% | 95.7% | 97.8% | 84.4% | 86.7% |
| 01 · Rock · 90 BPM | 86.6% | 98.3% | 98.5% | 95.9% | 97.9% |
| 02 · Funk · 97 BPM | 32.6% | 42.4% | 98.0% | 77.2% | 63.7% |
| 03 · Bossa nova · 129 BPM | 51.2% | 96.9% | 97.9% | 85.6% | 95.8% |
| 04 · Rock · 142 BPM | 66.9% | 91.8% | 87.3% | 78.3% | 79.9% |
| 05 · Jazz · 150 BPM | 22.9% | 75.2% | 79.0% | 48.8% | 69.7% |

Per-performance table: intended major/minor agreement, with out-of-gamut reference spans excluded. The Funk performed annotation contains power-chord and suspended voicings; the instructed chart is major chords. BTC returned `N` over 16.93 seconds of that 29.69-second performance. ChordMini generated 61 intervals versus six instructed segments there, and 77 versus sixteen on Jazz. The baseline generated 107–351 intervals per performance. These raw event counts show display-stability concerns but are **not boundary accuracy scores**.

The two Rock performances were useful for all stronger models, particularly the simpler 90 BPM performance. The complex Jazz performance was harder for every candidate. These findings support proceeding with a curated beginner song/arrangement pilot while retaining several candidates. They do not establish reliability on arbitrary YouTube songs, vocals, electric-guitar effects or full-band mixes.

No source separation, key hints, additional smoothing, tuning, training, confidence calibration, beat snapping or founder guitar ratings were added. CREMA and Chordino retain their native decoder behavior. ChordMini remains unsmoothed, as in the synthetic comparison.

## Data and reference semantics

The official [GuitarSet dataset record](https://zenodo.org/records/3371780) is version 1.1.0, DOI `10.5281/zenodo.3371780`, and lists **CC BY 4.0 for the dataset**. Its [helper-code repository](https://github.com/marl/GuitarSet) has an MIT license. The paper's publication license and the code license were not used as substitutes for the dataset license.

The six originals were selected before inference to span all six performers and five styles, with two Rock performances and slow/fast tempi. Selection was based on filenames and metadata; no model prediction was used to choose them:

| Original file stem | Microphone audio seconds | Intended / performed segments |
|---|---:|---:|
| `00_SS3-84-Bb_comp` | 45.708 | 16 / 16 |
| `01_Rock1-90-C#_comp` | 32.000 | 6 / 6 |
| `02_Funk1-97-C_comp` | 29.688 | 6 / 6 |
| `03_BN1-129-Eb_comp` | 22.324 | 6 / 6 |
| `04_Rock2-142-D_comp` | 27.042 | 14 / 14 |
| `05_Jazz3-150-C_comp` | 25.600 | 16 / 16 |

Both JAMS annotations use namespace `chord`: the first is instructed/intended, the second is performed. The [official notebook](https://github.com/marl/GuitarSet/blob/master/visualize/plot_demo.ipynb) documents that order. The [dataset authors](https://guitarset.weebly.com/) explain that performed chord qualities are inferred from note annotations, while segmentation and roots are inherited from the instructed sheet. The [paper](https://guitarset.weebly.com/uploads/1/2/1/6/121620128/xi_ismir_2018.pdf), section 5.2.2, explicitly describes this bias and possible anticipation/lag. Consequently **no boundary or physical chord-onset accuracy is asserted in this pilot**.

The known-error performances `04_BN3-154-E_comp` and `04_Jazz1-200-B_comp` are excluded; the [official timing issue](https://github.com/marl/GuitarSet/issues/5) reports offsets of +0.409 and +0.309 seconds. The duplicated-note performance `02_Funk2-119-G_comp` from [issue 4](https://github.com/marl/GuitarSet/issues/4) is also excluded. These exclusions do not prove all other annotations are error-free.

GuitarSet contains studio-recorded acoustic guitar; players heard backing tracks through headphones. Microphone comping audio should not be described as a full commercial band mix. All six clips share one dataset and cannot establish generalization across recording environments.

## Label and input handling

Source microphone WAVs and JAMS files remain unchanged in the ignored `experiments/candidate-assets/guitarset` folder. FFmpeg created mono 22,050 Hz PCM16 copies without trimming, padding, gain changes or offset corrections. Source audio/JAMS hashes, prepared audio/reference hashes, source metadata and FFmpeg version are retained in the manifest/report. The tiny final annotation/sample rounding difference is clipped to prepared duration; unannotated time is unknown `X`, never an invented `N`.

Native Harte references are retained, including omitted notes, alterations, suspensions and relative bass degrees such as `/3`. CREMA's preserved native Harte labels are used directly. ChordMini checkpoint labels are validated as Harte when explicit, or converted from their documented implicit-major/display form. Baseline and Chordino display labels use an explicit quality map; absolute bass pitches such as `C/E` become the relative Harte degree `C:maj/3`. Unsupported labels fail visibly rather than acquiring guessed semantics. Missing detector intervals and `X` remain unknown and cannot earn silence credit.

The complete annotation ZIP matches official MD5 `b39b78e63d3446f2e54ddb7a54df9b10`; SHA-256 is `8daa02e6417ccca1685feb44b135e95928ad7037e5032ecb326b5791856fda99`. Only six microphone ZIP entries were downloaded using HTTP byte ranges; each passed ZIP CRC32 and has a recorded SHA-256. The full 656.9 MB microphone archive was not downloaded and its aggregate MD5 was not independently verified. The [JSON](GUITARSET_PILOT.json) contains all selected input hashes and source URLs; the [CSV](GUITARSET_PILOT.csv) contains all sixty scores.

## Model training overlap and runtime

The [BTC authors](https://github.com/jayg996/BTC-ISMIR19#data) list Isophonics, Robbie Williams and USPop2002 training/evaluation data. The [ChordMini paper](https://arxiv.org/html/2602.19778v1#S4.SS1) lists FMA, DALI and MAESTRO for unlabeled training, and Isophonics, Billboard, RWC Pop and USPop for labeled training. GuitarSet is not listed there. [CREMA's documentation](https://crema.readthedocs.io/en/stable/models.html) identifies its model lineage, but this review did not establish a complete checkpoint-specific training manifest. No independent GuitarSet training-overlap guarantee is made for the released checkpoints; this remains a diagnostic dataset, not a certified unseen holdout.

All models ran on CPU, sequentially, using their existing isolated environments and verified adapters/checkpoints/builds. Model loading is shared across batch clips where supported. Per-file runtime totals are retained, but BTC's first clip includes imports/model load, CREMA and ChordMini have separate setup times, and Chordino includes one plugin process per clip. These totals are not normalized estimates of production cloud costs.

ChordMini's initial sandboxed process failed during macOS OpenMP shared-memory initialization before inference. The same model/inputs/settings succeeded on a direct runtime retry outside the filesystem sandbox. The failed report/log are preserved in the local `attempts` folder and hashed in the final report; it is an environment failure, not a measured accuracy failure.

## Reproduce

Requires the six verified local original WAV/JAMS pairs above. Their official source archives are [annotation.zip](https://zenodo.org/api/records/3371780/files/annotation.zip/content) and [audio_mono-mic.zip](https://zenodo.org/api/records/3371780/files/audio_mono-mic.zip/content). Source audio belongs under `experiments/candidate-assets/guitarset/audio/{stem}_mic.wav`; source JAMS under `.../annotations/{stem}.jams`. Assets and model environments are local and ignored by Git; a fresh checkout must obtain them first.

From the repository root, this complete-archive route retrieves the same six originals. It downloads about 696 MB in total; it is a straightforward alternative to the bounded ZIP range retrieval used for this run. Resume interrupted downloads by repeating the curl commands. Both complete archive checksums are verified before extracting selected entries; Python's ZIP reader also verifies each entry's CRC.

```sh
mkdir -p experiments/candidate-assets/guitarset
curl --fail --location --retry 3 --continue-at - \
  https://zenodo.org/api/records/3371780/files/annotation.zip/content \
  --output experiments/candidate-assets/guitarset/annotation.zip
curl --fail --location --retry 3 --continue-at - \
  https://zenodo.org/api/records/3371780/files/audio_mono-mic.zip/content \
  --output experiments/candidate-assets/guitarset/audio_mono-mic.zip
python3 - <<'PY'
from pathlib import Path
import hashlib
import zipfile

assets = Path('experiments/candidate-assets/guitarset')
selected = ['00_SS3-84-Bb_comp', '01_Rock1-90-C#_comp', '02_Funk1-97-C_comp',
            '03_BN1-129-Eb_comp', '04_Rock2-142-D_comp', '05_Jazz3-150-C_comp']
archives = [('annotation.zip', 'b39b78e63d3446f2e54ddb7a54df9b10', 'annotations', '.jams'),
            ('audio_mono-mic.zip', '275966d6610ac34999b58426beb119c3', 'audio', '_mic.wav')]
for archive_name, expected_md5, folder, suffix in archives:
    archive = assets / archive_name
    with archive.open('rb') as stream:
        actual_md5 = hashlib.file_digest(stream, 'md5').hexdigest()
    if actual_md5 != expected_md5:
        raise ValueError(f'Incomplete or changed official archive: {archive_name}')
    destination = assets / folder
    destination.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as source:
        for stem in selected:
            name = stem + suffix
            entries = [entry for entry in source.infolist() if Path(entry.filename).name == name]
            if len(entries) != 1:
                raise ValueError(f'Missing/ambiguous official entry: {name}')
            content = source.read(entries[0])
            path = destination / name
            if path.exists() and path.read_bytes() != content:
                raise ValueError(f'Refusing to overwrite a different local input: {path}')
            if not path.exists():
                path.write_bytes(content)
            print(name, hashlib.sha256(content).hexdigest())
PY
```

The extraction snippet requires Python 3.11+ for `hashlib.file_digest`. `prepare` additionally verifies the selected WAV/JAMS SHA-256 values pinned in the pilot code. It preserves already verified prepared audio and refuses an existing `audio.wav` that lacks `source.json`, has changed, or has different source provenance.

The existing isolated `.venv-crema` contains the exact evaluation dependencies. A separate environment can instead install `experiments/analysis/requirements-pilot.txt`; the three pretrained candidate environments and native Chordino setup remain separate.

```sh
.venv-crema/bin/python experiments/analysis/guitarset_pilot.py prepare
.venv-crema/bin/python experiments/analysis/guitarset_pilot.py run
.venv-crema/bin/python -m unittest discover -s experiments/analysis/tests -p test_guitarset_pilot.py -v
```

`run` executes five batches sequentially and preserves unsuccessful cases. It returns a nonzero exit code if any reference comparison fails. If the platform produces the documented ChordMini OpenMP startup error, a normal direct invocation with the same manifest performs the retry:

```sh
.venv-chordmini/bin/python experiments/analysis/candidates/chordmini_adapter.py \
  --batch-manifest experiments/generated/guitarset-pilot/manifest.json \
  --output-root experiments/generated/guitarset-pilot
.venv-crema/bin/python experiments/analysis/guitarset_pilot.py run --reuse-existing
```

`--reuse-existing` scores saved predictions only; it verifies prepared audio, prediction input hashes, recording identity/duration and immutable reference hashes. It does not rerun inference. Eight focused tests verify bass semantics, vocabulary exclusions/coverage, separation of silence credit, unknown/missing intervals, unsupported labels, identity/timeline failures and refusal to overwrite unverified prepared audio.

## Next validation gate

Retain CREMA, BTC, Chordino and ChordMini for a larger permitted real-recording comparison rather than promoting one small-dataset winner. Expand to a frozen set with multiple recording environments and the app's intended rock/acoustic arrangements; keep full mixes and isolated-guitar tests as separate conditions. Test any source-separation, smoothing or soft-key hint on fixed screen cases, then evaluate untouched real holdouts. Report per-performance failures and reference coverage as well as averages. After reference checks, choose a few concrete chart comparisons for the founder's guitar sessions. Six short excerpts alone do not define a release gate.
