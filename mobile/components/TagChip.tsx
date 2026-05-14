import { View, Text } from "react-native";
import type { Tag, TagCategory } from "../services/types";

// Solid earth-toned chip backgrounds with cream text. Each category keeps
// a distinct hue but everything sits in the warm coffee family so the chips
// read clearly on the beige container (instead of the old translucent
// pastels which disappeared on a light background).
const TAG_COLORS: Record<TagCategory, { bg: string; text: string }> = {
  palette: { bg: "bg-[#9C5A5A]", text: "text-[#FBF6EE]" },     // dusty rose
  lighting: { bg: "bg-[#A66C3E]", text: "text-[#FBF6EE]" },    // copper
  texture: { bg: "bg-[#5A7368]", text: "text-[#FBF6EE]" },     // sage
  pattern: { bg: "bg-[#8B5A6F]", text: "text-[#FBF6EE]" },     // mauve
  silhouette: { bg: "bg-[#5A4429]", text: "text-[#FBF6EE]" },  // coffee
  material: { bg: "bg-[#7A6E3F]", text: "text-[#FBF6EE]" },    // olive
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
