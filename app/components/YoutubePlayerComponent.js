import React, { useRef } from "react";
import { Text, Button, View } from "react-native";
import YoutubePlayer from "react-native-youtube-iframe";

const YoutubePlayerComponent = ({
  videoUrl,
  onElapsedTimeUpdate,
  onPlaybackStateChange,
}) => {
  const playerRef = useRef(null);

  const videoId = getYoutubeId(videoUrl);

  const getElapsedTime = () => {
    playerRef.current?.getCurrentTime().then((currentTime) => {
      const elapsedMs = Math.floor(currentTime * 1000);
      const ms = elapsedMs % 1000;
      const min = Math.floor(elapsedMs / 60000);
      const seconds = Math.floor((elapsedMs - min * 60000) / 1000);

      const formattedTime = `${min.toString().padStart(2, "0")}:${seconds
        .toString()
        .padStart(2, "0")}:${ms.toString().padStart(3, "0")}`;
      onElapsedTimeUpdate(formattedTime);
    });
  };

  return (
    <View>
      {videoId ? (
        <>
          <YoutubePlayer
            ref={playerRef}
            height={300}
            videoId={videoId}
            onChangeState={(state) => {
              if (onPlaybackStateChange) {
                onPlaybackStateChange(state);
              }
            }}
          />
          <Button title="Get Current Time" onPress={getElapsedTime} />
        </>
      ) : (
        <Text>Invalid Video URL</Text>
      )}
    </View>
  );
};

// Function to extract YouTube video ID
const getYoutubeId = (url) => {
  const regExp =
    /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[2].length === 11 ? match[2] : null;
};

export default YoutubePlayerComponent;
