import {
  View,
  Text,
  FlatList,
  Image,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import { useVibeStore } from "../../stores/useVibeStore";
import type { VibeCheck } from "../../services/types";

function formatDate(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60));
      return minutes <= 1 ? "Just now" : `${minutes} min ago`;
    }
    return hours === 1 ? "1 hour ago" : `${hours} hours ago`;
  }
  if (days === 1) return "Yesterday";
  if (days < 7) return `${days} days ago`;

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  });
}

interface VibeHistoryCardProps {
  vibeCheck: VibeCheck;
  onPress: () => void;
}

function VibeHistoryCard({ vibeCheck, onPress }: VibeHistoryCardProps) {
  const primaryVibe = vibeCheck.vibes[0];
  const thumbnailUri = vibeCheck.photos[0];

  return (
    <Pressable
      onPress={onPress}
      className="flex-row bg-dark-800 rounded-2xl overflow-hidden border border-dark-700 active:opacity-80"
    >
      {thumbnailUri ? (
        <Image
          source={{ uri: thumbnailUri }}
          className="w-24 h-24"
          resizeMode="cover"
        />
      ) : (
        <View className="w-24 h-24 bg-dark-700 items-center justify-center">
          <Ionicons name="image" size={24} color="#64748b" />
        </View>
      )}

      <View className="flex-1 p-3 justify-center">
        <View className="flex-row items-center mb-1">
          <Ionicons
            name={vibeCheck.mode === "room" ? "home" : "shirt"}
            size={12}
            color="#6366f1"
          />
          <Text className="text-primary-400 text-xs ml-1 capitalize">
            {vibeCheck.mode}
          </Text>
          <Text className="text-dark-600 mx-2">·</Text>
          <Text className="text-dark-500 text-xs">
            {formatDate(new Date(vibeCheck.createdAt))}
          </Text>
        </View>

        <Text className="text-white font-bold text-lg capitalize mb-1">
          {primaryVibe?.aesthetic || "Unknown"}
        </Text>

        <View className="flex-row items-center">
          <View className="flex-row items-center mr-3">
            <Ionicons name="images" size={12} color="#64748b" />
            <Text className="text-dark-400 text-xs ml-1">
              {vibeCheck.photos.length}
            </Text>
          </View>
          <View className="flex-row items-center">
            <Ionicons name="pricetag" size={12} color="#64748b" />
            <Text className="text-dark-400 text-xs ml-1">
              {vibeCheck.tags.length} tags
            </Text>
          </View>
        </View>
      </View>

      <View className="justify-center pr-3">
        <Ionicons name="chevron-forward" size={20} color="#64748b" />
      </View>
    </Pressable>
  );
}

export default function HistoryScreen() {
  const { vibeHistory, clearHistory } = useVibeStore();

  const handleVibePress = (vibeCheck: VibeCheck) => {
    router.push(`/vibe/${vibeCheck.id}`);
  };

  if (vibeHistory.length === 0) {
    return (
      <SafeAreaView className="flex-1 bg-dark-900 items-center justify-center px-8">
        <View className="w-20 h-20 rounded-full bg-dark-800 items-center justify-center mb-6">
          <Ionicons name="time" size={40} color="#64748b" />
        </View>
        <Text className="text-white text-xl font-bold text-center mb-2">
          No Vibe Checks Yet
        </Text>
        <Text className="text-dark-400 text-center mb-8">
          Your past vibe checks will appear here. Start by checking your first
          vibe!
        </Text>
        <Pressable
          onPress={() => router.push("/")}
          className="bg-primary-500 px-8 py-4 rounded-2xl"
        >
          <Text className="text-white font-bold text-lg">
            Check Your Vibe
          </Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-dark-900">
      <FlatList
        data={vibeHistory}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <VibeHistoryCard
            vibeCheck={item}
            onPress={() => handleVibePress(item)}
          />
        )}
        contentContainerStyle={{ padding: 16, gap: 12 }}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={
          <View className="flex-row items-center justify-between mb-4">
            <Text className="text-dark-400 text-sm">
              {vibeHistory.length} vibe check{vibeHistory.length !== 1 ? "s" : ""}
            </Text>
            <Pressable
              onPress={() => {
                clearHistory();
              }}
              className="flex-row items-center"
            >
              <Ionicons name="trash-outline" size={16} color="#ef4444" />
              <Text className="text-red-400 text-sm ml-1">Clear</Text>
            </Pressable>
          </View>
        }
      />
    </SafeAreaView>
  );
}
