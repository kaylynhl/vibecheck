import { View, Text, Image, Pressable, ScrollView, Linking, Alert } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { Item } from "../services/types";

interface ItemCardProps {
  item: Item;
  onPress?: () => void;
}

async function openProductUrl(item: Item) {
  if (!item.productUrl) {
    Alert.alert("No link", "This item doesn't have a product page.");
    return;
  }
  try {
    const supported = await Linking.canOpenURL(item.productUrl);
    if (!supported) {
      Alert.alert("Can't open link", item.productUrl);
      return;
    }
    await Linking.openURL(item.productUrl);
  } catch (err) {
    Alert.alert("Couldn't open", String(err));
  }
}

export function ItemCard({ item, onPress }: ItemCardProps) {
  const matchPercent = Math.round(item.matchScore * 100);
  const handlePress = onPress ?? (() => openProductUrl(item));

  return (
    <Pressable
      onPress={handlePress}
      className="w-40 bg-dark-800 rounded-2xl overflow-hidden border border-dark-700 active:opacity-80"
    >
      <View className="relative">
        <Image
          source={{ uri: item.imageUrl }}
          className="w-full h-40"
          resizeMode="cover"
        />
        <View className="absolute top-2 right-2 bg-dark-200/85 px-2 py-1 rounded-full">
          <Text className="text-xs text-[#F5EFE6] font-semibold">
            {matchPercent}% match
          </Text>
        </View>
      </View>

      <View className="p-3">
        <Text
          className="text-dark-200 font-semibold text-sm mb-1"
          numberOfLines={2}
        >
          {item.name}
        </Text>

        <View className="flex-row items-center justify-between">
          {item.price && (
            <Text className="text-primary-700 font-bold text-sm">
              {item.price}
            </Text>
          )}
          {item.source && (
            <Text className="text-dark-500 text-xs">{item.source}</Text>
          )}
        </View>

        <View className="flex-row flex-wrap gap-1 mt-2">
          {item.tags.slice(0, 2).map((tag) => (
            <View key={tag} className="bg-dark-700 px-2 py-0.5 rounded">
              <Text className="text-dark-400 text-xs">{tag}</Text>
            </View>
          ))}
        </View>
      </View>
    </Pressable>
  );
}

interface ItemListProps {
  items: Item[];
  title?: string;
  onItemPress?: (item: Item) => void;
}

export function ItemList({
  items,
  title = "Recommended Items",
  onItemPress,
}: ItemListProps) {
  return (
    <View>
      <View className="flex-row items-center justify-between mb-3 px-4">
        <Text
          className="text-dark-200 text-xl"
          style={{ fontFamily: "PlayfairDisplay_600SemiBold" }}
        >
          {title}
        </Text>
        <Pressable className="flex-row items-center">
          <Text className="text-primary-500 text-sm mr-1">See all</Text>
          <Ionicons name="chevron-forward" size={16} color="#8B6F47" />
        </Pressable>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={{ paddingHorizontal: 16, gap: 12 }}
      >
        {items.map((item) => (
          <ItemCard
            key={item.id}
            item={item}
            onPress={
              onItemPress ? () => onItemPress(item) : () => openProductUrl(item)
            }
          />
        ))}
      </ScrollView>
    </View>
  );
}
