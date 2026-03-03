import { useEffect, useState } from "react";
import {
  View,
  Text,
  ScrollView,
  Image,
  Pressable,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useLocalSearchParams, router } from "expo-router";
import { Ionicons } from "@expo/vector-icons";
import {
  TagCloud,
  VibeList,
  ItemList,
  PlaylistCard,
} from "../../components";
import { useVibeStore } from "../../stores/useVibeStore";
import { vibeApi } from "../../services/api";
import type { VibeCheck } from "../../services/types";

export default function VibeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { currentVibeCheck, getVibeById } = useVibeStore();
  const [vibeData, setVibeData] = useState<VibeCheck | null>(null);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  useEffect(() => {
    if (currentVibeCheck?.id === id) {
      setVibeData(currentVibeCheck);
    } else if (id) {
      const fromHistory = getVibeById(id);
      if (fromHistory) {
        setVibeData(fromHistory);
      }
    }
  }, [id, currentVibeCheck, getVibeById]);

  const handleFeedback = async (type: "good" | "bad") => {
    if (!vibeData) return;

    const feedback = {
      vibeMatch: type === "good" ? 5 : 1,
      itemsHelpful: type === "good",
      playlistMatch: type === "good",
    };

    await vibeApi.submitFeedback(vibeData.id, feedback);
    setFeedbackSubmitted(true);
    Alert.alert(
      "Thanks for your feedback!",
      "Your input helps us improve VibeCheck."
    );
  };

  if (!vibeData) {
    return (
      <SafeAreaView className="flex-1 bg-dark-900 items-center justify-center">
        <Ionicons name="alert-circle" size={48} color="#64748b" />
        <Text className="text-dark-400 mt-4">Vibe check not found</Text>
        <Pressable
          onPress={() => router.back()}
          className="mt-4 bg-primary-500 px-6 py-3 rounded-full"
        >
          <Text className="text-white font-semibold">Go Back</Text>
        </Pressable>
      </SafeAreaView>
    );
  }

  const primaryVibe = vibeData.vibes[0];

  return (
    <SafeAreaView className="flex-1 bg-dark-900">
      <ScrollView
        className="flex-1"
        showsVerticalScrollIndicator={false}
      >
        <View className="relative h-56">
          <ScrollView
            horizontal
            pagingEnabled
            showsHorizontalScrollIndicator={false}
            className="flex-1"
          >
            {vibeData.photos.map((photo, index) => (
              <Image
                key={photo}
                source={{ uri: photo }}
                className="w-screen h-56"
                resizeMode="cover"
              />
            ))}
          </ScrollView>

          <View className="absolute bottom-4 left-0 right-0 flex-row justify-center">
            {vibeData.photos.map((_, index) => (
              <View
                key={index}
                className={`w-2 h-2 rounded-full mx-1 ${
                  index === 0 ? "bg-white" : "bg-white/40"
                }`}
              />
            ))}
          </View>

          <View className="absolute top-4 left-4 bg-dark-900/80 px-3 py-1.5 rounded-full flex-row items-center">
            <Ionicons
              name={vibeData.mode === "room" ? "home" : "shirt"}
              size={14}
              color="#6366f1"
            />
            <Text className="text-white text-sm font-medium ml-1.5 capitalize">
              {vibeData.mode}
            </Text>
          </View>
        </View>

        <View className="px-4 -mt-8">
          <View className="bg-dark-800 rounded-2xl p-5 border border-dark-700 mb-6">
            <Text className="text-xs text-primary-400 uppercase tracking-wide mb-2">
              Your Dominant Vibe
            </Text>
            <Text className="text-white text-3xl font-bold capitalize mb-2">
              {primaryVibe?.aesthetic}
            </Text>
            <Text className="text-dark-400 text-sm">
              {Math.round((primaryVibe?.confidence || 0) * 100)}% confidence
            </Text>
          </View>

          <View className="mb-8">
            <Text className="text-white font-bold text-lg mb-4">
              Aesthetic Breakdown
            </Text>
            <VibeList vibes={vibeData.vibes} />
          </View>

          <View className="mb-8">
            <Text className="text-white font-bold text-lg mb-4">
              Visual Tags
            </Text>
            <View className="bg-dark-800 rounded-2xl p-4 border border-dark-700">
              <TagCloud tags={vibeData.tags} showConfidence />
            </View>
          </View>
        </View>

        <View className="mb-8">
          <ItemList
            items={vibeData.itemRecommendations}
            title={
              vibeData.mode === "room"
                ? "Complete the Look"
                : "Style Suggestions"
            }
          />
        </View>

        <View className="px-4 mb-8">
          <Text className="text-white font-bold text-lg mb-4">
            Your Vibe Playlist
          </Text>
          <PlaylistCard playlist={vibeData.playlistRecommendation} />
        </View>

        {!feedbackSubmitted && (
          <View className="px-4 mb-8">
            <View className="bg-dark-800 rounded-2xl p-5 border border-dark-700">
              <Text className="text-white font-bold text-lg mb-2 text-center">
                How'd we do?
              </Text>
              <Text className="text-dark-400 text-sm text-center mb-4">
                Your feedback helps improve VibeCheck
              </Text>
              <View className="flex-row justify-center gap-4">
                <Pressable
                  onPress={() => handleFeedback("good")}
                  className="flex-1 bg-green-500/20 py-3 rounded-xl items-center flex-row justify-center active:bg-green-500/30"
                >
                  <Ionicons name="thumbs-up" size={20} color="#22c55e" />
                  <Text className="text-green-400 font-semibold ml-2">
                    Nailed it
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => handleFeedback("bad")}
                  className="flex-1 bg-red-500/20 py-3 rounded-xl items-center flex-row justify-center active:bg-red-500/30"
                >
                  <Ionicons name="thumbs-down" size={20} color="#ef4444" />
                  <Text className="text-red-400 font-semibold ml-2">
                    Not quite
                  </Text>
                </Pressable>
              </View>
            </View>
          </View>
        )}

        <View className="px-4 pb-8">
          <Pressable
            onPress={() => router.push("/")}
            className="bg-primary-500 py-4 rounded-2xl items-center active:opacity-90"
          >
            <Text className="text-white font-bold text-lg">
              Check Another Vibe
            </Text>
          </Pressable>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
