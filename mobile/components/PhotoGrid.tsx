import { View, Image, Pressable, Text } from "react-native";
import { Ionicons } from "@expo/vector-icons";

interface PhotoGridProps {
  photos: string[];
  onRemovePhoto?: (uri: string) => void;
  onAddPhoto?: () => void;
  maxPhotos?: number;
  editable?: boolean;
}

export function PhotoGrid({
  photos,
  onRemovePhoto,
  onAddPhoto,
  maxPhotos = 6,
  editable = true,
}: PhotoGridProps) {
  const canAddMore = photos.length < maxPhotos;

  if (photos.length === 0) {
    return (
      <Pressable
        onPress={onAddPhoto}
        className="h-64 bg-dark-800 rounded-2xl border-2 border-dashed border-dark-600 items-center justify-center active:border-primary-500"
      >
        <View className="items-center">
          <View className="w-16 h-16 rounded-full bg-dark-700 items-center justify-center mb-4">
            <Ionicons name="camera" size={32} color="#6366f1" />
          </View>
          <Text className="text-white font-semibold text-lg mb-1">
            Add Photos
          </Text>
          <Text className="text-dark-400 text-sm text-center px-8">
            Take or select photos of your room or outfit
          </Text>
        </View>
      </Pressable>
    );
  }

  const gridCols = photos.length === 1 ? 1 : 2;

  return (
    <View className="gap-2">
      <View
        className="flex-row flex-wrap"
        style={{ gap: 8 }}
      >
        {photos.map((uri, index) => (
          <View
            key={uri}
            className="relative"
            style={{
              width: gridCols === 1 ? "100%" : "48%",
              aspectRatio: gridCols === 1 ? 16 / 9 : 1,
            }}
          >
            <Image
              source={{ uri }}
              className="w-full h-full rounded-xl"
              resizeMode="cover"
            />

            {editable && onRemovePhoto && (
              <Pressable
                onPress={() => onRemovePhoto(uri)}
                className="absolute top-2 right-2 w-8 h-8 rounded-full bg-dark-900/80 items-center justify-center active:bg-red-500"
              >
                <Ionicons name="close" size={18} color="white" />
              </Pressable>
            )}

            <View className="absolute bottom-2 left-2 bg-dark-900/80 px-2 py-1 rounded">
              <Text className="text-white text-xs font-medium">
                {index + 1}/{photos.length}
              </Text>
            </View>
          </View>
        ))}

        {editable && canAddMore && (
          <Pressable
            onPress={onAddPhoto}
            className="items-center justify-center bg-dark-800 rounded-xl border-2 border-dashed border-dark-600 active:border-primary-500"
            style={{
              width: photos.length === 0 ? "100%" : "48%",
              aspectRatio: 1,
            }}
          >
            <Ionicons name="add" size={32} color="#6366f1" />
            <Text className="text-dark-400 text-xs mt-1">Add more</Text>
          </Pressable>
        )}
      </View>

      {photos.length > 0 && (
        <Text className="text-dark-500 text-xs text-center mt-1">
          {photos.length} photo{photos.length !== 1 ? "s" : ""} selected
          {maxPhotos && ` (max ${maxPhotos})`}
        </Text>
      )}
    </View>
  );
}
