import { View, Text, Pressable, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { useVibeStore } from "../../stores/useVibeStore";

interface SettingsItemProps {
  icon: keyof typeof Ionicons.glyphMap;
  title: string;
  subtitle?: string;
  onPress?: () => void;
  showArrow?: boolean;
}

function SettingsItem({
  icon,
  title,
  subtitle,
  onPress,
  showArrow = true,
}: SettingsItemProps) {
  return (
    <Pressable
      onPress={onPress}
      className="flex-row items-center py-4 active:opacity-70"
    >
      <View className="w-10 h-10 rounded-full bg-dark-700 items-center justify-center mr-4">
        <Ionicons name={icon} size={20} color="#8B6F47" />
      </View>
      <View className="flex-1">
        <Text className="text-dark-200 font-medium">{title}</Text>
        {subtitle && (
          <Text className="text-dark-400 text-sm mt-0.5">{subtitle}</Text>
        )}
      </View>
      {showArrow && (
        <Ionicons name="chevron-forward" size={20} color="#8B6F47" />
      )}
    </Pressable>
  );
}

export default function ProfileScreen() {
  const { vibeHistory } = useVibeStore();

  const topVibes = vibeHistory
    .flatMap((check) => check.vibes)
    .reduce(
      (acc, vibe) => {
        acc[vibe.aesthetic] = (acc[vibe.aesthetic] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    );

  const sortedVibes = Object.entries(topVibes)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 3);

  return (
    <SafeAreaView className="flex-1 bg-dark-900">
      <ScrollView
        contentContainerStyle={{ padding: 16 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="items-center mb-8">
          <View className="w-24 h-24 rounded-full bg-primary-500 items-center justify-center mb-4">
            <Ionicons name="person" size={48} color="white" />
          </View>
          <Text
            className="text-dark-200 text-2xl"
            style={{ fontFamily: "PlayfairDisplay_700Bold" }}
          >
            VibeChecker
          </Text>
          <Text className="text-dark-400 text-sm">
            {vibeHistory.length} vibe checks completed
          </Text>
        </View>

        {sortedVibes.length > 0 && (
          <View className="bg-dark-800 rounded-2xl p-4 border border-dark-700 mb-6">
            <Text className="text-dark-400 text-xs uppercase tracking-wide mb-3">
              Your Top Vibes
            </Text>
            <View className="gap-2">
              {sortedVibes.map(([aesthetic, count], index) => (
                <View key={aesthetic} className="flex-row items-center">
                  <View
                    className={`w-6 h-6 rounded-full items-center justify-center mr-3 ${
                      index === 0
                        ? "bg-primary-500"
                        : index === 1
                          ? "bg-dark-600"
                          : "bg-dark-700"
                    }`}
                  >
                    <Text
                      className={`text-xs font-bold ${
                        index === 0 ? "text-white" : "text-dark-200"
                      }`}
                    >
                      {index + 1}
                    </Text>
                  </View>
                  <Text className="text-dark-200 font-medium capitalize flex-1">
                    {aesthetic}
                  </Text>
                  <Text className="text-dark-400 text-sm">
                    {count}x
                  </Text>
                </View>
              ))}
            </View>
          </View>
        )}

        <View className="bg-dark-800 rounded-2xl border border-dark-700 px-4">
          <SettingsItem
            icon="notifications-outline"
            title="Notifications"
            subtitle="Get updates on new features"
          />
          <View className="h-px bg-dark-700" />
          <SettingsItem
            icon="color-palette-outline"
            title="Appearance"
            subtitle="Dark mode (always on)"
          />
          <View className="h-px bg-dark-700" />
          <SettingsItem
            icon="shield-checkmark-outline"
            title="Privacy"
            subtitle="Your data stays on device"
          />
          <View className="h-px bg-dark-700" />
          <SettingsItem
            icon="information-circle-outline"
            title="About VibeCheck"
            subtitle="Version 1.0.0"
          />
        </View>

        <View className="mt-8 items-center">
          <Text className="text-dark-500 text-xs text-center">
            Built for CS4701 AI Practicum
          </Text>
          <Text className="text-dark-600 text-xs text-center mt-1">
            Julia, Sennet, Kaylyn
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
