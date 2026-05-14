import "../global.css";
import { useEffect } from "react";
import { Text, TextInput } from "react-native";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import * as SplashScreen from "expo-splash-screen";
import {
  useFonts,
  Lora_400Regular,
  Lora_500Medium,
  Lora_600SemiBold,
  Lora_700Bold,
  Lora_400Regular_Italic,
} from "@expo-google-fonts/lora";
import {
  PlayfairDisplay_600SemiBold,
  PlayfairDisplay_700Bold,
  PlayfairDisplay_800ExtraBold,
} from "@expo-google-fonts/playfair-display";

// Warm coffee-shop palette. Keep these in sync with tailwind.config.js so
// that native screens (Stack header, splash, etc.) match the NativeWind UI.
const THEME = {
  cream: "#F5EFE6",
  beige: "#E8DDCB",
  espresso: "#2B1810",
  caramel: "#8B6F47",
};

SplashScreen.preventAutoHideAsync().catch(() => {
  // ignore -- splash may already be hidden in dev
});

// Apply Lora as the default font across every <Text> / <TextInput> so that
// individual components don't need to opt in. Per-instance `style` /
// `className` still overrides this default (e.g. headings using font-display).
function applyDefaultFont() {
  const defaultStyle = { fontFamily: "Lora_400Regular", color: THEME.espresso };
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const TextAny = Text as any;
  TextAny.defaultProps = TextAny.defaultProps || {};
  TextAny.defaultProps.style = [defaultStyle, TextAny.defaultProps.style];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const TextInputAny = TextInput as any;
  TextInputAny.defaultProps = TextInputAny.defaultProps || {};
  TextInputAny.defaultProps.style = [defaultStyle, TextInputAny.defaultProps.style];
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    Lora_400Regular,
    Lora_500Medium,
    Lora_600SemiBold,
    Lora_700Bold,
    Lora_400Regular_Italic,
    PlayfairDisplay_600SemiBold,
    PlayfairDisplay_700Bold,
    PlayfairDisplay_800ExtraBold,
  });

  useEffect(() => {
    if (fontsLoaded || fontError) {
      applyDefaultFont();
      SplashScreen.hideAsync().catch(() => {});
    }
  }, [fontsLoaded, fontError]);

  if (!fontsLoaded && !fontError) {
    // Splash screen stays up while Google Fonts are loading.
    return null;
  }

  return (
    <GestureHandlerRootView style={{ flex: 1, backgroundColor: THEME.cream }}>
      <StatusBar style="dark" />
      <Stack
        screenOptions={{
          headerStyle: {
            backgroundColor: THEME.beige,
          },
          headerTintColor: THEME.espresso,
          headerTitleStyle: {
            fontFamily: "PlayfairDisplay_700Bold",
            fontWeight: "700",
            color: THEME.espresso,
          },
          contentStyle: {
            backgroundColor: THEME.cream,
          },
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="vibe/[id]"
          options={{
            title: "Your Vibe",
            presentation: "card",
            // iOS otherwise shows "(tabs)" as the back label since that's
            // the previous route's name. Give it a friendly label instead.
            headerBackTitle: "Home",
          }}
        />
      </Stack>
    </GestureHandlerRootView>
  );
}
