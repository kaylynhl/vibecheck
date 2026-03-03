import { View, Text, Image, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { Playlist, Track } from "../services/types";

function formatDuration(ms: number): string {
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

interface TrackRowProps {
  track: Track;
  index: number;
  onPress?: () => void;
}

function TrackRow({ track, index, onPress }: TrackRowProps) {
  return (
    <Pressable
      onPress={onPress}
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

      {track.durationMs && (
        <Text className="text-dark-500 text-xs">
          {formatDuration(track.durationMs)}
        </Text>
      )}

      <Pressable className="ml-3 p-1">
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
  const totalDuration = playlist.tracks.reduce(
    (acc, track) => acc + (track.durationMs || 0),
    0
  );
  const totalMinutes = Math.floor(totalDuration / 60000);

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

          <View className="flex-row gap-2 mt-3">
            <Pressable
              onPress={onPlay}
              className="bg-primary-500 px-4 py-2 rounded-full flex-row items-center"
            >
              <Ionicons name="play" size={14} color="white" />
              <Text className="text-white font-semibold text-sm ml-1">
                Play
              </Text>
            </Pressable>

            <Pressable
              onPress={onOpenInSpotify}
              className="bg-dark-700 px-4 py-2 rounded-full flex-row items-center"
            >
              <Ionicons name="open-outline" size={14} color="#64748b" />
              <Text className="text-dark-300 font-medium text-sm ml-1">
                Open
              </Text>
            </Pressable>
          </View>
        </View>
      </View>

      <View className="border-t border-dark-700 px-4 py-2">
        {playlist.tracks.slice(0, 5).map((track, index) => (
          <TrackRow key={track.id} track={track} index={index} />
        ))}

        {playlist.tracks.length > 5 && (
          <Pressable className="py-3 items-center">
            <Text className="text-primary-400 font-medium text-sm">
              View all {playlist.tracks.length} tracks
            </Text>
          </Pressable>
        )}
      </View>
    </View>
  );
}
