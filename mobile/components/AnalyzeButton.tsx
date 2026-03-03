import { Pressable, Text, ActivityIndicator, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface AnalyzeButtonProps {
  onPress: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  photoCount?: number;
}

export function AnalyzeButton({
  onPress,
  isLoading = false,
  disabled = false,
  photoCount = 0,
}: AnalyzeButtonProps) {
  const isDisabled = disabled || isLoading || photoCount === 0;

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      className={`py-4 px-6 rounded-2xl flex-row items-center justify-center ${
        isDisabled
          ? "bg-dark-700"
          : "bg-gradient-to-r from-primary-500 to-accent-purple active:opacity-90"
      }`}
      style={
        !isDisabled
          ? {
              shadowColor: "#6366f1",
              shadowOffset: { width: 0, height: 4 },
              shadowOpacity: 0.3,
              shadowRadius: 8,
              elevation: 8,
            }
          : undefined
      }
    >
      {isLoading ? (
        <>
          <ActivityIndicator color="white" size="small" />
          <Text className="text-white font-bold text-lg ml-3">
            Analyzing...
          </Text>
        </>
      ) : (
        <>
          <View className="w-10 h-10 rounded-full bg-white/20 items-center justify-center mr-3">
            <Ionicons
              name="sparkles"
              size={20}
              color={isDisabled ? "#64748b" : "white"}
            />
          </View>
          <View>
            <Text
              className={`font-bold text-lg ${
                isDisabled ? "text-dark-500" : "text-white"
              }`}
            >
              Check My Vibe
            </Text>
            {photoCount > 0 && (
              <Text
                className={`text-xs ${
                  isDisabled ? "text-dark-600" : "text-white/70"
                }`}
              >
                {photoCount} photo{photoCount !== 1 ? "s" : ""} ready
              </Text>
            )}
          </View>
        </>
      )}
    </Pressable>
  );
}
