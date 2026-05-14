import { View, Text, Pressable } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { VibeMode } from "../services/types";

interface ModeToggleProps {
  mode: VibeMode;
  onModeChange: (mode: VibeMode) => void;
}

export function ModeToggle({ mode, onModeChange }: ModeToggleProps) {
  return (
    <View className="flex-row bg-dark-800 rounded-xl p-1">
      <Pressable
        onPress={() => onModeChange("room")}
        className={`flex-1 flex-row items-center justify-center py-3 px-4 rounded-lg ${
          mode === "room" ? "bg-primary-500" : "bg-transparent"
        }`}
      >
        <Ionicons
          name="home"
          size={18}
          color={mode === "room" ? "white" : "#8B6F47"}
        />
        <Text
          className={`ml-2 font-semibold ${
            mode === "room" ? "text-white" : "text-dark-400"
          }`}
        >
          Room
        </Text>
      </Pressable>

      <Pressable
        onPress={() => onModeChange("outfit")}
        className={`flex-1 flex-row items-center justify-center py-3 px-4 rounded-lg ${
          mode === "outfit" ? "bg-primary-500" : "bg-transparent"
        }`}
      >
        <Ionicons
          name="shirt"
          size={18}
          color={mode === "outfit" ? "white" : "#8B6F47"}
        />
        <Text
          className={`ml-2 font-semibold ${
            mode === "outfit" ? "text-white" : "text-dark-400"
          }`}
        >
          Outfit
        </Text>
      </Pressable>
    </View>
  );
}
