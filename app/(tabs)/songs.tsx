import React from "react";
import { Link } from "expo-router";

import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  Dimensions,
  StyleSheet,
} from "react-native";
import { useNavigation } from "@react-navigation/native";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";

const { width: screenWidth } = Dimensions.get("window");

interface Song {
  title: string;
  artist: string;
  chords: string[];
  videoUrl: string;
}

type RootStackParamList = {
  SongPlayer: { song: Song };
};

type SongsScreenNavigationProp = NativeStackNavigationProp<
  RootStackParamList,
  "SongPlayer"
>;

const Songs = () => {
  const navigation = useNavigation<SongsScreenNavigationProp>();

  const songsDae: Song[] = [
    {
      title: "Feelin' Alright?",
      artist: "Joe Cocker",
      chords: ["A", "D"],
      videoUrl: "https://www.youtube.com/watch?v=jvAByzXT1U8",
    },
    {
      title: "Sweet Home Alabama",
      artist: "Lynyrd Skynyrd",
      chords: ["D", "C", "G"],
      videoUrl: "https://www.youtube.com/watch?v=ye5BuYf8q4o",
    },
    {
      title: "Brown Eyed Girl",
      artist: "Van Morrison",
      chords: ["G", "C", "D", "E"],
      videoUrl: "https://www.youtube.com/watch?v=UfmkgQRmmeE",
    },
    {
      title: "Wonderwall",
      artist: "Oasis",
      chords: ["Em", "G", "D", "A"],
      videoUrl: "https://www.youtube.com/watch?v=bx1Bh8ZvH84",
    },
  ];

  const songsMinor: Song[] = [
    {
      title: "Hallelujah",
      artist: "Leonard Cohen",
      chords: ["C", "Am", "F", "G"],
      videoUrl: "https://www.youtube.com/watch?v=YrLk4vdY28Q",
    },
    {
      title: "Creep",
      artist: "Radiohead",
      chords: ["G", "B", "C", "Cm"],
      videoUrl: "https://www.youtube.com/watch?v=XFkzRNyygfk",
    },
    {
      title: "House of the Rising Sun",
      artist: "The Animals",
      chords: ["Am", "C", "D", "F"],
      videoUrl: "https://www.youtube.com/watch?v=4-43lLKaqBQ",
    },
  ];

  const renderSongList = (songs: Song[], title: string) => (
    <View style={styles.sectionContainer}>
      <Text style={styles.sectionTitle}>{title}</Text>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollViewContent}
      >
        {songs.map((song, index) => (
          <Link
            key={index}
            href={{
              pathname: "/screens/SongPlayer",
              params: {
                id: index.toString(),
                title: song.title,
                artist: song.artist,
                chords: song.chords.join(","),
                videoUrl: song.videoUrl,
              },
            }}
            asChild
          >
            <TouchableOpacity style={styles.songCard}>
              <Image
                source={{
                  uri: `https://img.youtube.com/vi/${getYoutubeId(
                    song.videoUrl
                  )}/0.jpg`,
                }}
                style={styles.thumbnail}
                resizeMode="cover"
              />
              <Text style={styles.songTitle} numberOfLines={1}>
                {song.title}
              </Text>
              <Text style={styles.artistName} numberOfLines={1}>
                {song.artist}
              </Text>
              <Text style={styles.chords} numberOfLines={1}>
                {song.chords.join(", ")}
              </Text>
            </TouchableOpacity>
          </Link>
        ))}
      </ScrollView>
    </View>
  );

  return (
    <ScrollView style={styles.container}>
      {renderSongList(songsDae, "Songs with D, A, E Chords")}
      {renderSongList(songsMinor, "Songs with Am, Em, Dm Chords")}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 20,
  },
  sectionContainer: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 20,
    fontWeight: "bold",
    marginHorizontal: 10,
    marginBottom: 10,
  },
  scrollViewContent: {
    paddingHorizontal: 10,
  },
  songCard: {
    marginRight: 15,
    width: screenWidth * 0.4,
    marginBottom: 10,
  },
  thumbnail: {
    width: "100%",
    height: (screenWidth * 0.4 * 9) / 16,
    borderRadius: 8,
  },
  songTitle: {
    marginTop: 5,
    fontWeight: "bold",
    fontSize: 14,
  },
  artistName: {
    fontSize: 12,
  },
  chords: {
    fontSize: 12,
    color: "gray",
  },
});

export default Songs;

function getYoutubeId(url: string): string {
  const regExp =
    /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|\&v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[2].length === 11 ? match[2] : "";
}
