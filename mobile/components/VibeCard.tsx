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
          ? "bg-primary-500 border border-primary-600"
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
            className={`text-xl capitalize ${
              isTop ? "text-white" : "text-dark-200"
            }`}
            style={{ fontFamily: "PlayfairDisplay_600SemiBold" }}
          >
            {vibe.aesthetic}
          </Text>
        </View>
        <Text
          className={`text-sm font-semibold ${
            isTop ? "text-white/85" : "text-dark-400"
          }`}
        >
          {confidencePercent}%
        </Text>
      </View>

      <View
        className={`h-2 rounded-full overflow-hidden mb-3 ${
          isTop ? "bg-primary-700/40" : "bg-dark-700"
        }`}
      >
        <View
          className={`h-full rounded-full ${
            isTop ? "bg-white" : "bg-primary-500"
          }`}
          style={{ width: `${confidencePercent}%` }}
        />
      </View>

      {vibe.description && (
        <Text
          className={`text-sm leading-relaxed ${
            isTop ? "text-white/85" : "text-dark-400"
          }`}
        >
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
