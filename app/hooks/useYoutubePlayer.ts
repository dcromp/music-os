import { useState, useRef, useCallback, useEffect } from "react";

export const useYoutubePlayer = (videoId: string) => {
  const [playerInstance, setPlayerInstance] = useState<any>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [videoStarted, setVideoStarted] = useState(false);
  const isMounted = useRef(true);

  useEffect(() => {
    return () => {
      isMounted.current = false;
    };
  }, []);

  const onPlayerReady = useCallback((ref: any) => {
    setPlayerInstance(ref);
  }, []);

  const onStateChange = useCallback(
    (state: number) => {
      if (state === 1) {
        setIsPlaying(true);
        if (!videoStarted) {
          setVideoStarted(true);
        }
      } else {
        setIsPlaying(false);
      }
    },
    [videoStarted]
  );

  return {
    playerInstance,
    isPlaying,
    videoStarted,
    onPlayerReady,
    onStateChange,
  };
};
