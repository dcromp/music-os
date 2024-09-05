import React, {
  useState,
  useRef,
  useEffect,
  useCallback,
  memo,
  useMemo,
} from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
  Platform,
  StatusBar,
} from "react-native";
import YoutubePlayer from "react-native-youtube-iframe";
import { useLocalSearchParams, Link } from "expo-router";

export interface Song {
  id: string;
  title: string;
  artist: string;
  chords: string[];
  thumbnailUrl: string;
  videoUrl: string;
}

const MemoizedYoutubePlayer = memo(
  ({ videoId, onReady }: { videoId: string; onReady: (ref: any) => void }) => {
    const playerRef = useRef<any>(null);

    useEffect(() => {
      if (playerRef.current) {
        onReady(playerRef.current);
      }
      return () => {
        if (playerRef.current && playerRef.current.destroy) {
          playerRef.current.destroy();
        }
      };
    }, [onReady]);

    return <YoutubePlayer height={300} videoId={videoId} ref={playerRef} />;
  }
);

const ElapsedTime = memo(({ elapsed }: { elapsed: string }) => (
  <Text style={styles.timestamp}>Current Time: {elapsed}</Text>
));

const SongInfo = memo(({ song }: { song: Song }) => (
  <>
    <Text style={styles.title}>{song.title}</Text>
    <Text style={styles.artist}>{song.artist}</Text>
    <Text style={styles.chords}>Chords: {song.chords.join(", ")}</Text>
  </>
));

const SongPlayer = () => {
  const params = useLocalSearchParams<{
    id: string;
    title: string;
    artist: string;
    chords: string;
    thumbnailUrl: string;
    videoUrl: string;
  }>();

  const [elapsed, setElapsed] = useState("00:00:000");
  const [playerInstance, setPlayerInstance] = useState<any>(null);
  const isMounted = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Memoize song object to avoid unnecessary recalculations
  const song: Song = useMemo(
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

  const videoId = useMemo(() => getYoutubeId(song.videoUrl), [song.videoUrl]);

  useEffect(() => {
    console.log("Video URL:", song.videoUrl);
    console.log("Video ID:", videoId);
  }, [song.videoUrl, videoId]);

  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (playerInstance) {
        playerInstance.destroy(); // Destroy the player instance
      }
    };
  }, [playerInstance]);

  // Memoized version of updateElapsedTime
  const updateElapsedTime = useCallback(async () => {
    if (playerInstance && isMounted.current) {
      try {
        const elapsed_sec = await playerInstance.getCurrentTime();
        const elapsed_ms = Math.floor(elapsed_sec * 1000);
        const ms = elapsed_ms % 1000;
        const min = Math.floor(elapsed_ms / 60000);
        const seconds = Math.floor((elapsed_ms - min * 60000) / 1000);

        setElapsed(
          `${min.toString().padStart(2, "0")}:${seconds
            .toString()
            .padStart(2, "0")}:${ms.toString().padStart(3, "0")}`
        );
      } catch (error) {
        console.error("Error getting current time from YouTube player:", error);
      }
    }
  }, [playerInstance]);

  // Move setInterval into onReady
  const onPlayerReady = useCallback(
    (ref: any) => {
      setPlayerInstance(ref);

      if (intervalRef.current) {
        clearInterval(intervalRef.current); // Clear any previous intervals
      }

      intervalRef.current = setInterval(updateElapsedTime, 1000);
    },
    [updateElapsedTime]
  );

  // Remove this useEffect as it's redundant with the cleanup in the first useEffect
  // useEffect(() => {
  //   return () => {
  //     if (intervalRef.current) {
  //       clearInterval(intervalRef.current);
  //     }
  //   };
  // }, []);

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.container}>
        <Link href="/" asChild>
          <TouchableOpacity style={styles.backButton}>
            <Text style={styles.backButtonText}>← Back</Text>
          </TouchableOpacity>
        </Link>
        {videoId && (
          <MemoizedYoutubePlayer videoId={videoId} onReady={onPlayerReady} />
        )}
        <SongInfo song={song} />
        <ElapsedTime elapsed={elapsed} />
      </View>
    </SafeAreaView>
  );
};

const getYoutubeId = (url: string): string | null => {
  const regExp =
    /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[2].length === 11 ? match[2] : null;
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: "#fff", // or any color that matches your app's theme
  },
  container: {
    flex: 1,
    padding: 10,
    paddingTop: Platform.OS === "android" ? StatusBar.currentHeight : 0,
  },
  backButton: {
    marginBottom: 10,
    paddingVertical: 10, // Increase touch area
  },
  backButtonText: {
    fontSize: 18,
    color: "blue",
  },
  title: { fontSize: 20, fontWeight: "bold", marginTop: 10 },
  artist: { fontSize: 16, marginTop: 5 },
  chords: { fontSize: 16, marginTop: 10 },
  timestamp: { fontSize: 16, marginTop: 10, fontWeight: "bold" },
});

export default memo(SongPlayer);
