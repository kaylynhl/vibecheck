import { View, Text } from "react-native";
import type { Tag, TagCategory } from "../services/types";

const TAG_COLORS: Record<TagCategory, { bg: string; text: string }> = {
  palette: { bg: "bg-pink-500/20", text: "text-pink-400" },
  lighting: { bg: "bg-orange-500/20", text: "text-orange-400" },
  texture: { bg: "bg-teal-500/20", text: "text-teal-400" },
  pattern: { bg: "bg-purple-500/20", text: "text-purple-400" },
  silhouette: { bg: "bg-indigo-500/20", text: "text-indigo-400" },
  material: { bg: "bg-lime-500/20", text: "text-lime-400" },
};

interface TagChipProps {
  tag: Tag;
  showConfidence?: boolean;
  size?: "sm" | "md" | "lg";
}

export function TagChip({ tag, showConfidence = false, size = "md" }: TagChipProps) {
  const colors = TAG_COLORS[tag.category] || TAG_COLORS.palette;

  const sizeClasses = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base",
  };

  return (
    <View
      className={`${colors.bg} rounded-full flex-row items-center ${sizeClasses[size]}`}
    >
      <Text className={`${colors.text} font-medium`}>{tag.value}</Text>
      {showConfidence && (
        <Text className={`${colors.text} opacity-60 ml-1 text-xs`}>
          {Math.round(tag.confidence * 100)}%
        </Text>
      )}
    </View>
  );
}
