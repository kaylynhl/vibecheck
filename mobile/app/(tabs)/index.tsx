import { useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { router } from "expo-router";
import * as ImagePicker from "expo-image-picker";
import { PhotoGrid, ModeToggle, AnalyzeButton } from "../../components";
import { useVibeStore } from "../../stores/useVibeStore";
import { vibeApi } from "../../services/api";

export default function HomeScreen() {
  const {
    selectedPhotos,
    mode,
    isAnalyzing,
    addPhoto,
    removePhoto,
    clearPhotos,
    setMode,
    setIsAnalyzing,
    setCurrentVibeCheck,
    addToHistory,
  } = useVibeStore();

  const [cameraPermission, setCameraPermission] = useState<boolean | null>(null);

  const requestPermissions = useCallback(async () => {
    const cameraStatus = await ImagePicker.requestCameraPermissionsAsync();
    const mediaStatus = await ImagePicker.requestMediaLibraryPermissionsAsync();
    setCameraPermission(
      cameraStatus.status === "granted" && mediaStatus.status === "granted"
    );
    return (
      cameraStatus.status === "granted" && mediaStatus.status === "granted"
    );
  }, []);

  const handleAddPhoto = useCallback(async () => {
    const hasPermission = cameraPermission ?? (await requestPermissions());

    if (!hasPermission) {
      Alert.alert(
        "Permission Required",
        "Please grant camera and photo library permissions to use VibeCheck."
      );
      return;
    }

    Alert.alert(
      "Add Photo",
      "Choose how you'd like to add a photo",
      [
        {
          text: "Take Photo",
          onPress: async () => {
            const result = await ImagePicker.launchCameraAsync({
              mediaTypes: "images",
              allowsEditing: true,
              aspect: [4, 3],
              quality: 0.8,
            });

            if (!result.canceled && result.assets[0]) {
              addPhoto(result.assets[0].uri);
            }
          },
        },
        {
          text: "Choose from Library",
          onPress: async () => {
            const result = await ImagePicker.launchImageLibraryAsync({
              mediaTypes: "images",
              allowsMultipleSelection: true,
              selectionLimit: 6 - selectedPhotos.length,
              quality: 0.8,
            });

            if (!result.canceled) {
              result.assets.forEach((asset) => {
                addPhoto(asset.uri);
              });
            }
          },
        },
        { text: "Cancel", style: "cancel" },
      ]
    );
  }, [cameraPermission, requestPermissions, addPhoto, selectedPhotos.length]);

  const handleAnalyze = useCallback(async () => {
    if (selectedPhotos.length === 0) {
      Alert.alert("No Photos", "Please add at least one photo to analyze.");
      return;
    }

    setIsAnalyzing(true);

    try {
      const response = await vibeApi.analyzePhotos(selectedPhotos, mode);

      if (response.success && response.data) {
        setCurrentVibeCheck(response.data);
        addToHistory(response.data);
        clearPhotos();
        router.push(`/vibe/${response.data.id}`);
      } else {
        Alert.alert("Error", response.error || "Failed to analyze photos.");
      }
    } catch (error) {
      Alert.alert("Error", "Something went wrong. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  }, [
    selectedPhotos,
    mode,
    setIsAnalyzing,
    setCurrentVibeCheck,
    addToHistory,
    clearPhotos,
  ]);

  return (
    <SafeAreaView className="flex-1 bg-dark-900">
      <ScrollView
        className="flex-1"
        contentContainerStyle={{ padding: 16, paddingBottom: 32 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="mb-6">
          <Text className="text-dark-400 text-sm mb-1">What are we checking?</Text>
          <ModeToggle mode={mode} onModeChange={setMode} />
        </View>

        <View className="mb-6">
          <Text className="text-dark-400 text-sm mb-3">
            {mode === "room"
              ? "Add photos of your room or space"
              : "Add photos of your outfit (front, back, details)"}
          </Text>
          <PhotoGrid
            photos={selectedPhotos}
            onAddPhoto={handleAddPhoto}
            onRemovePhoto={removePhoto}
            maxPhotos={6}
          />
        </View>

        {selectedPhotos.length > 1 && (
          <View className="mb-6 bg-dark-800 rounded-xl p-4">
            <View className="flex-row items-center">
              <View className="w-8 h-8 rounded-full bg-primary-500/20 items-center justify-center mr-3">
                <Text className="text-primary-400">✨</Text>
              </View>
              <View className="flex-1">
                <Text className="text-white font-medium text-sm">
                  Multi-photo analysis
                </Text>
                <Text className="text-dark-400 text-xs">
                  We'll combine insights from all {selectedPhotos.length} photos for better accuracy
                </Text>
              </View>
            </View>
          </View>
        )}

        <AnalyzeButton
          onPress={handleAnalyze}
          isLoading={isAnalyzing}
          photoCount={selectedPhotos.length}
        />

        <View className="mt-8">
          <Text className="text-dark-500 text-xs text-center leading-relaxed">
            VibeCheck will analyze your photos to identify the aesthetic,
            suggest complementary items, and create a matching playlist.
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
