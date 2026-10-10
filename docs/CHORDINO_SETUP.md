# Chordino / NNLS-Chroma candidate status

**Pending setup; not benchmarked.** The Mac currently has no `sonic-annotator` executable, no Vamp plugin folder in the checked system/user paths, and no Vamp SDK headers under Homebrew. Those checks establish missing prerequisites, not an algorithm-quality result.

The [official c4dm/nnls-chroma repository](https://github.com/c4dm/nnls-chroma) supplies Chordino as a Vamp plugin. It combines NNLS harmonic features with chord-template matching and optional HMM/Viterbi or heuristic smoothing. It is a useful additional comparison to the simple baseline and neural models.

Next setup step: obtain or build an Apple Silicon-compatible Vamp host and the official plugin in a project-local directory, record versions and validate label/timestamp output, then add a common-schema adapter and run the same 64 cases. No system-wide installation has been performed. Worker setup was interrupted by account usage limits; no Chordino source build or inference failure is claimed.

The repository's GPL terms do not exclude an internal benchmark. Deployment/distribution obligations are a separate decision. Keep this candidate in the shortlist until tested or explicitly deferred, and never assign it a synthetic score from another algorithm.
