import React, { useMemo, useState } from "react";
import {
  View,
  SafeAreaView,
  TouchableOpacity,
  Text,
  StyleSheet,
  Platform,
  StatusBar,
} from "react-native";
import { useLocalSearchParams, Link } from "expo-router";
import YoutubePlayerComponent from "../components/YoutubePlayerComponent";
import ChordProgressionDisplay from "../components/ChordProgressionDisplay";

const SongPlayer = () => {
  const params = useLocalSearchParams();

  const [elapsedTime, setElapsedTime] = useState("00:00:000");
  const [isPlaying, setIsPlaying] = useState(false); // Track the playing state

  const song = useMemo(
    () => ({
      id: params.id || "",
      title: params.title || "",
      artist: params.artist || "",
      chords: params.chords ? params.chords.split(",") : [],
      thumbnailUrl: params.thumbnailUrl || "",
      videoUrl: params.videoUrl || "",
    }),
    [
      params.id,
      params.title,
      params.artist,
      params.chords,
      params.thumbnailUrl,
      params.videoUrl,
    ]
  );

  const handleElapsedTimeUpdate = (time) => {
    setElapsedTime(time);
  };

  const handlePlaybackStateChange = (state) => {
    setIsPlaying(state === "playing"); // Update based on the state
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Link href="/" asChild>
          <TouchableOpacity style={styles.backButton}>
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>
        </Link>

        <YoutubePlayerComponent
          videoUrl={song.videoUrl}
          onElapsedTimeUpdate={handleElapsedTimeUpdate}
          onPlaybackStateChange={handlePlaybackStateChange} // Pass playback state change handler
        />

        <Text style={styles.timestamp}>Current Time: {elapsedTime}</Text>

        {/* Pass the playing state down to ChordProgressionDisplay */}
        <ChordProgressionDisplay isPlaying={isPlaying} />
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#fff",
  },
  container: {
    flex: 1,
    padding: 10,
    paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0,
  },
  backButton: {
    marginBottom: 10,
    paddingVertical: 10,
  },
  backButtonText: {
    fontSize: 18,
    color: "blue",
  },
  timestamp: {
    fontSize: 16,
    marginTop: 10,
    fontWeight: "bold",
  },
});

export default SongPlayer;
