import { useState } from "react";
import { View, Text, Image, Pressable, Linking, Alert } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import * as WebBrowser from "expo-web-browser";
import type { Playlist, Track } from "../services/types";
import { spotifyApi } from "../services/spotify";

// Hide the "Save to Spotify" button when no client ID is configured, so the
// user never taps a button that's guaranteed to fail. Set
// `EXPO_PUBLIC_SPOTIFY_CLIENT_ID` in mobile/.env to enable saving.
const SPOTIFY_SAVE_ENABLED = Boolean(
  process.env.EXPO_PUBLIC_SPOTIFY_CLIENT_ID
);

function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

// Spotify's public embed player serves the 30s preview audio under its own
// auth context (same trick Discord uses). Works for signed-out users, no
// OAuth required. Pass the track ID, not the full spotify_url.
function spotifyEmbedUrl(trackId: string): string {
  return `https://open.spotify.com/embed/track/${trackId}`;
}

async function openInSpotify(url: string | undefined) {
  if (!url) {
    Alert.alert("No link", "No Spotify URL for this track.");
    return;
  }
  try {
    await Linking.openURL(url);
  } catch (err) {
    Alert.alert("Couldn't open Spotify", String(err));
  }
}

async function openEmbedPreview(track: Track) {
  if (!track.id) {
    Alert.alert("No preview", "No track ID available.");
    return;
  }
  try {
    await WebBrowser.openBrowserAsync(spotifyEmbedUrl(track.id), {
      dismissButtonStyle: "close",
      presentationStyle: WebBrowser.WebBrowserPresentationStyle.PAGE_SHEET,
      controlsColor: "#1DB954",
    });
  } catch (err) {
    Alert.alert("Couldn't open preview", String(err));
  }
}

interface TrackRowProps {
  track: Track;
  index: number;
}

function TrackRow({ track, index }: TrackRowProps) {
  return (
    <Pressable
      onPress={() => openInSpotify(track.spotifyUrl)}
      className="flex-row items-center py-2 active:opacity-70"
    >
      <Text className="text-dark-500 w-6 text-sm">{index + 1}</Text>

      {track.albumArt ? (
        <Image
          source={{ uri: track.albumArt }}
          className="w-10 h-10 rounded mr-3"
        />
      ) : (
        <View className="w-10 h-10 rounded bg-dark-700 mr-3 items-center justify-center">
          <Ionicons name="musical-note" size={16} color="#64748b" />
        </View>
      )}

      <View className="flex-1">
        <Text className="text-white font-medium text-sm" numberOfLines={1}>
          {track.name}
        </Text>
        <Text className="text-dark-400 text-xs" numberOfLines={1}>
          {track.artist}
        </Text>
      </View>

      {track.durationMs ? (
        <Text className="text-dark-500 text-xs">
          {formatDuration(track.durationMs)}
        </Text>
      ) : null}

      <Pressable
        onPress={() => openEmbedPreview(track)}
        hitSlop={8}
        className="ml-3 p-1"
      >
        <Ionicons name="play-circle" size={24} color="#6366f1" />
      </Pressable>
    </Pressable>
  );
}

interface PlaylistCardProps {
  playlist: Playlist;
  onPlay?: () => void;
  onOpenInSpotify?: () => void;
}

export function PlaylistCard({
  playlist,
  onPlay,
  onOpenInSpotify,
}: PlaylistCardProps) {
  const [saving, setSaving] = useState(false);

  const totalDuration = playlist.tracks.reduce(
    (acc, track) => acc + (track.durationMs || 0),
    0
  );
  const totalMinutes = Math.floor(totalDuration / 60000);
  const firstTrack = playlist.tracks[0];

  const handlePlay =
    onPlay ?? (() => (firstTrack ? openEmbedPreview(firstTrack) : null));
  const handleOpen =
    onOpenInSpotify ??
    (() => openInSpotify(firstTrack?.spotifyUrl));

  const handleSave = async () => {
    if (saving) return;
    setSaving(true);
    try {
      const result = await spotifyApi.savePlaylistToLibrary(playlist);
      if (result.ok) {
        Alert.alert(
          "Saved to Spotify",
          `"${playlist.name}" is now in your library.`,
          [
            { text: "OK" },
            ...(result.playlistUrl
              ? [
                  {
                    text: "Open it",
                    onPress: () => Linking.openURL(result.playlistUrl!),
                  },
                ]
              : []),
          ]
        );
      } else {
        Alert.alert("Couldn't save", result.error);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <View className="bg-dark-800 rounded-2xl overflow-hidden border border-dark-700">
      <View className="flex-row p-4">
        {playlist.coverImage ? (
          <Image
            source={{ uri: playlist.coverImage }}
            className="w-24 h-24 rounded-xl"
          />
        ) : (
          <View className="w-24 h-24 rounded-xl bg-gradient-to-br from-primary-600 to-accent-purple items-center justify-center">
            <Ionicons name="musical-notes" size={40} color="white" />
          </View>
        )}

        <View className="flex-1 ml-4 justify-center">
          <Text className="text-xs text-primary-400 uppercase tracking-wide mb-1">
            Playlist for {playlist.aesthetic}
          </Text>
          <Text className="text-white font-bold text-lg mb-1">
            {playlist.name}
          </Text>
          <Text className="text-dark-400 text-sm">
            {playlist.tracks.length} tracks · {totalMinutes} min
          </Text>

          <View className="flex-row gap-2 mt-3 flex-wrap">
            <Pressable
              onPress={handlePlay}
              className="bg-primary-500 px-4 py-2 rounded-full flex-row items-center"
            >
              <Ionicons name="play" size={14} color="white" />
              <Text className="text-white font-semibold text-sm ml-1">
                Preview
              </Text>
            </Pressable>

            <Pressable
              onPress={handleOpen}
              className="bg-dark-700 px-4 py-2 rounded-full flex-row items-center"
            >
              <Ionicons name="open-outline" size={14} color="#64748b" />
              <Text className="text-dark-300 font-medium text-sm ml-1">
                Open
              </Text>
            </Pressable>
          </View>

          {SPOTIFY_SAVE_ENABLED && (
            <Pressable
              onPress={handleSave}
              disabled={saving}
              className="bg-[#1DB954] px-4 py-2 rounded-full flex-row items-center mt-2 self-start active:opacity-80"
            >
              <Ionicons
                name={saving ? "hourglass-outline" : "add-circle"}
                size={14}
                color="white"
              />
              <Text className="text-white font-semibold text-sm ml-1.5">
                {saving ? "Saving…" : "Save to Spotify"}
              </Text>
            </Pressable>
          )}
        </View>
      </View>

      <View className="border-t border-dark-700 px-4 py-2">
        {playlist.tracks.map((track, index) => (
          <TrackRow key={track.id} track={track} index={index} />
        ))}
      </View>
    </View>
  );
}
