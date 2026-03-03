import { View, Text } from "react-native";
import type { Tag, TagCategory } from "../services/types";
import { TagChip } from "./TagChip";

interface TagCloudProps {
  tags: Tag[];
  groupByCategory?: boolean;
  showConfidence?: boolean;
}

const CATEGORY_LABELS: Record<TagCategory, string> = {
  palette: "Color Palette",
  lighting: "Lighting",
  texture: "Texture",
  pattern: "Pattern",
  silhouette: "Silhouette",
  material: "Material",
};

export function TagCloud({
  tags,
  groupByCategory = true,
  showConfidence = false,
}: TagCloudProps) {
  if (!groupByCategory) {
    return (
      <View className="flex-row flex-wrap gap-2">
        {tags.map((tag) => (
          <TagChip key={tag.id} tag={tag} showConfidence={showConfidence} />
        ))}
      </View>
    );
  }

  const groupedTags = tags.reduce(
    (acc, tag) => {
      if (!acc[tag.category]) {
        acc[tag.category] = [];
      }
      acc[tag.category].push(tag);
      return acc;
    },
    {} as Record<TagCategory, Tag[]>
  );

  const categories = Object.keys(groupedTags) as TagCategory[];

  return (
    <View className="gap-4">
      {categories.map((category) => (
        <View key={category}>
          <Text className="text-dark-400 text-xs uppercase tracking-wide mb-2">
            {CATEGORY_LABELS[category]}
          </Text>
          <View className="flex-row flex-wrap gap-2">
            {groupedTags[category].map((tag) => (
              <TagChip
                key={tag.id}
                tag={tag}
                showConfidence={showConfidence}
                size="sm"
              />
            ))}
          </View>
        </View>
      ))}
    </View>
  );
}
