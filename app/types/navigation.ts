import { Song } from "../screens/SongPlayer";

export type RootStackParamList = {
  SongPlayer: {
    title: string;
    artist: string;
    chords: string;
    thumbnailUrl: string;
  };
  // Add other routes here
};
