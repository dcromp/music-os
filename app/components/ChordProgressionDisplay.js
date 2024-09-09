import React, { useState, useMemo, memo, useCallback, useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { useTimer } from "react-use-precision-timer";
import sampleSongData from "../data/sampleSongData.json";

const Beat = memo(({ chord, isCurrentBeat }) => (
  <View style={[styles.beat, isCurrentBeat && styles.currentBeat]}>
    <Text style={styles.chordText}>{chord}</Text>
  </View>
));

const Bar = memo(({ chords, currentBeat, isCurrentBar }) => (
  <View style={styles.bar}>
    {[0, 1, 2, 3].map((beatIndex) => (
      <Beat
        key={beatIndex}
        chord={chords[beatIndex] || ""}
        isCurrentBeat={isCurrentBar && beatIndex === currentBeat}
      />
    ))}
  </View>
));

const ChordProgressionDisplay = memo(({ isPlaying }) => {
  const [currentBar, setCurrentBar] = useState(0);
  const [currentBeat, setCurrentBeat] = useState(0);

  const song = sampleSongData;
  const chordProgressions = song.chordProgressions || [];

  const updateBeatAndBar = useCallback(() => {
    setCurrentBeat((prevBeat) => {
      const newBeat = (prevBeat + 1) % 4;
      if (newBeat === 0) {
        setCurrentBar((prevBar) => (prevBar + 1) % chordProgressions.length);
      }
      return newBeat;
    });
  }, [chordProgressions.length]);

  const msPerBeat = useMemo(() => 60000 / song.tempo, [song.tempo]);

  const timer = useTimer({ delay: msPerBeat }, updateBeatAndBar);

  useEffect(() => {
    if (isPlaying) {
      timer.start();
    } else {
      timer.pause();
    }

    return () => {
      timer.stop();
    };
  }, [isPlaying, timer]);

  const getBarChords = useMemo(() => {
    return chordProgressions.map((progression) => progression.chord);
  }, [chordProgressions]);

  const visibleBars = useMemo(() => {
    const barsToShow = 4;
    const startIndex = currentBar;
    const endIndex = (startIndex + barsToShow) % chordProgressions.length;

    if (endIndex > startIndex) {
      return getBarChords.slice(startIndex, startIndex + barsToShow);
    } else {
      return [
        ...getBarChords.slice(startIndex),
        ...getBarChords.slice(
          0,
          barsToShow - (chordProgressions.length - startIndex)
        ),
      ];
    }
  }, [chordProgressions, currentBar, getBarChords]);

  if (chordProgressions.length === 0) {
    return <Text>No Chord Progression Available</Text>;
  }

  return (
    <View style={styles.container}>
      <View style={styles.progressionContainer}>
        {visibleBars.map((chord, index) => (
          <Bar
            key={index}
            chords={Array(4).fill(chord)}
            currentBeat={index === 0 ? currentBeat : -1}
            isCurrentBar={index === 0}
          />
        ))}
      </View>
    </View>
  );
});

const styles = StyleSheet.create({
  container: {
    height: 220, // Adjust this value based on your bar height (4 * 50 + some margin)
    justifyContent: "flex-start",
    alignItems: "stretch",
  },
  progressionContainer: {
    flexDirection: "column", // Changed to column to display bars vertically
    justifyContent: "center",
    alignItems: "center",
    marginTop: 20,
  },
  bar: {
    flexDirection: "row",
    borderWidth: 1,
    borderColor: "#ccc",
    marginBottom: 5,
  },
  beat: {
    flex: 1,
    height: 50,
    justifyContent: "center",
    alignItems: "center",
    borderRightWidth: 1,
    borderRightColor: "#ccc",
  },
  currentBeat: {
    backgroundColor: "#e6e6e6",
  },
  chordText: {
    fontSize: 16,
    fontWeight: "bold",
  },
  currentBar: {
    borderColor: "#007AFF",
    borderWidth: 2,
  },
});

export default ChordProgressionDisplay;
