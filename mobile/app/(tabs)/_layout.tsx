import { Tabs } from "expo-router";
import { Ionicons } from "@expo/vector-icons";

// Warm coffee-shop palette. Mirrors THEME in app/_layout.tsx and the
// remapped tokens in tailwind.config.js.
const COLORS = {
  cream: "#F5EFE6",
  beige: "#E8DDCB",
  tan: "#D4C5B0",
  espresso: "#2B1810",
  caramel: "#8B6F47",
  muted: "#8B6F47",
};

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: COLORS.caramel,
        tabBarInactiveTintColor: COLORS.muted,
        tabBarStyle: {
          backgroundColor: COLORS.beige,
          borderTopColor: COLORS.tan,
          borderTopWidth: 1,
          paddingBottom: 8,
          paddingTop: 8,
          height: 88,
        },
        tabBarLabelStyle: {
          fontFamily: "Lora_600SemiBold",
          fontSize: 12,
          fontWeight: "600",
        },
        headerStyle: {
          backgroundColor: COLORS.beige,
        },
        headerTintColor: COLORS.espresso,
        headerTitleStyle: {
          fontFamily: "PlayfairDisplay_700Bold",
          fontWeight: "700",
          color: COLORS.espresso,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: "VibeCheck",
          tabBarLabel: "Check",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="camera" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: "History",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="time" size={size} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: "Profile",
          tabBarIcon: ({ color, size }) => (
            <Ionicons name="person" size={size} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
