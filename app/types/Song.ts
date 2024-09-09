export interface ChordProgression {
  startTime: number;
  endTime: number;
  chord: string;
}

export default interface Song {
  id: string;
  title: string;
  artist: string;
  chords: string[];
  thumbnailUrl: string;
  videoUrl: string;
  tempo: number;
  timeSignature: string;
  beatsPerBar: number;
  chordProgressions: ChordProgression[];
}
