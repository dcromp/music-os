import { useState, useRef, useCallback, useEffect } from "react";

export const useTimeSynchronization = (
  playerInstance: any,
  isPlaying: boolean
) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [localCurrentTime, setLocalCurrentTime] = useState(0);
  const [elapsed, setElapsed] = useState("00:00:000");
  const startTimeRef = useRef(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const localIntervalRef = useRef<NodeJS.Timeout | null>(null);

  const updateLocalTime = useCallback(() => {
    if (isPlaying) {
      const now = Date.now();
      setLocalCurrentTime(now - startTimeRef.current);
    }
  }, [isPlaying]);

  const syncWithYouTube = useCallback(async () => {
    if (playerInstance) {
      try {
        const elapsed_sec = await playerInstance.getCurrentTime();
        const elapsed_ms = Math.floor(elapsed_sec * 1000);

        startTimeRef.current = Date.now() - elapsed_ms;
        setCurrentTime(elapsed_ms);
        setLocalCurrentTime(elapsed_ms);

        const min = Math.floor(elapsed_ms / 60000);
        const seconds = Math.floor((elapsed_ms % 60000) / 1000);
        const ms = elapsed_ms % 1000;

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

  useEffect(() => {
    intervalRef.current = setInterval(syncWithYouTube, 1000);
    localIntervalRef.current = setInterval(updateLocalTime, 50);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
      if (localIntervalRef.current) clearInterval(localIntervalRef.current);
    };
  }, [syncWithYouTube, updateLocalTime]);

  return { currentTime, localCurrentTime, elapsed };
};
