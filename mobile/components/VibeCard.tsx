import { View, Text } from "react-native";
import type { VibeResult } from "../services/types";

interface VibeCardProps {
  vibe: VibeResult;
  rank: number;
  isTop?: boolean;
}

export function VibeCard({ vibe, rank, isTop = false }: VibeCardProps) {
  const confidencePercent = Math.round(vibe.confidence * 100);

  return (
    <View
      className={`rounded-2xl p-4 ${
        isTop
          ? "bg-gradient-to-r from-primary-600/30 to-accent-purple/30 border border-primary-500/50"
          : "bg-dark-800/80 border border-dark-700"
      }`}
    >
      <View className="flex-row items-center justify-between mb-2">
        <View className="flex-row items-center gap-2">
          <View
            className={`w-6 h-6 rounded-full items-center justify-center ${
              isTop ? "bg-primary-500" : "bg-dark-600"
            }`}
          >
            <Text
              className={`text-xs font-bold ${
                isTop ? "text-white" : "text-dark-300"
              }`}
            >
              {rank}
            </Text>
          </View>
          <Text
            className={`text-lg font-bold capitalize ${
              isTop ? "text-white" : "text-dark-200"
            }`}
          >
            {vibe.aesthetic}
          </Text>
        </View>
        <Text
          className={`text-sm font-semibold ${
            isTop ? "text-primary-300" : "text-dark-400"
          }`}
        >
          {confidencePercent}%
        </Text>
      </View>

      <View className="h-2 bg-dark-700 rounded-full overflow-hidden mb-3">
        <View
          className={`h-full rounded-full ${
            isTop
              ? "bg-gradient-to-r from-primary-500 to-accent-purple"
              : "bg-dark-500"
          }`}
          style={{ width: `${confidencePercent}%` }}
        />
      </View>

      {vibe.description && (
        <Text className="text-dark-400 text-sm leading-relaxed">
          {vibe.description}
        </Text>
      )}
    </View>
  );
}

interface VibeListProps {
  vibes: VibeResult[];
}

export function VibeList({ vibes }: VibeListProps) {
  return (
    <View className="gap-3">
      {vibes.map((vibe, index) => (
        <VibeCard
          key={vibe.aesthetic}
          vibe={vibe}
          rank={index + 1}
          isTop={index === 0}
        />
      ))}
    </View>
  );
}
