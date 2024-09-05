declare module "react-native-youtube-iframe" {
  import { ComponentType, Ref } from "react";

  interface YoutubeIframeProps {
    height: number;
    videoId: string;
    ref?: Ref<any>;
    // Add other props as needed
  }

  const YoutubePlayer: ComponentType<YoutubeIframeProps>;

  export default YoutubePlayer;
}
