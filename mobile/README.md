# VibeCheck Mobile App

React Native Expo iOS app for the VibeCheck aesthetic classification and recommendation system.

## Features

- **Photo Capture**: Take photos or select from library (supports multiple photos)
- **Mode Selection**: Choose between Room or Outfit analysis
- **Vibe Analysis**: Get predicted aesthetics with confidence scores
- **Visual Tags**: See interpretable tags (palette, lighting, texture, pattern, etc.)
- **Item Recommendations**: Get personalized item suggestions matching your vibe
- **Playlist Recommendations**: Discover music that matches your aesthetic
- **History**: View and revisit past vibe checks
- **Feedback**: Rate results for human study evaluation

## Tech Stack

- **Framework**: React Native with Expo SDK 55
- **Navigation**: Expo Router (file-based routing)
- **Styling**: NativeWind (Tailwind CSS for React Native)
- **State Management**: Zustand
- **Camera**: expo-camera + expo-image-picker
- **TypeScript**: Full type safety

## Getting Started

### Prerequisites

- Node.js 18+
- npm or yarn
- Expo CLI (`npm install -g expo-cli`)
- iOS Simulator (Xcode) or Expo Go app on your device

### Installation

```bash
cd mobile
npm install
```

### Running the App

```bash
# Start the development server
npm start

# Run on iOS Simulator
npm run ios

# Run on Android Emulator
npm run android

# Run in web browser
npm run web
```

## Project Structure

```
mobile/
├── app/                    # Expo Router pages
│   ├── (tabs)/             # Tab navigation screens
│   │   ├── index.tsx       # Home/Capture screen
│   │   ├── history.tsx     # Past vibe checks
│   │   └── profile.tsx     # User profile
│   ├── vibe/[id].tsx       # Vibe result detail
│   └── _layout.tsx         # Root layout
├── components/             # Reusable UI components
│   ├── PhotoGrid.tsx       # Multi-photo display
│   ├── TagChip.tsx         # Individual tag chip
│   ├── TagCloud.tsx        # Grouped tags display
│   ├── VibeCard.tsx        # Aesthetic result card
│   ├── ItemCard.tsx        # Recommended item
│   ├── PlaylistCard.tsx    # Playlist display
│   ├── ModeToggle.tsx      # Room/Outfit toggle
│   └── AnalyzeButton.tsx   # Main CTA button
├── services/
│   ├── api.ts              # API service layer
│   └── types.ts            # TypeScript interfaces
├── stores/
│   └── useVibeStore.ts     # Zustand state store
├── mocks/                  # Mock data for development
│   ├── vibes.ts            # Aesthetic mock data
│   ├── tags.ts             # Tag mock data
│   ├── items.ts            # Item recommendations
│   └── playlists.ts        # Playlist mock data
└── assets/                 # App icons and images
```

## Backend Integration

The app currently uses mock data. To connect to the Python backend:

1. Set the `EXPO_PUBLIC_API_URL` environment variable:
   ```bash
   export EXPO_PUBLIC_API_URL=http://your-backend-url:8000
   ```

2. The API service in `services/api.ts` will automatically use the backend when available, falling back to mock data if unavailable.

### Expected API Endpoint

```
POST /api/analyze
Content-Type: multipart/form-data

Body:
- mode: "room" | "outfit"
- photos: File[]

Response:
{
  id: string,
  photos: string[],
  mode: string,
  tags: Tag[],
  vibes: VibeResult[],
  itemRecommendations: Item[],
  playlistRecommendation: Playlist,
  createdAt: string
}
```

## Supported Aesthetics

The app recognizes various aesthetics including:
- Cottagecore
- Dark Academia
- Minimalist
- Y2K
- Coastal Grandmother
- Indie Sleaze
- Clean Girl
- Bohemian
- Old Money
- Grunge
- And more...

## Development

### Adding New Aesthetics

1. Add aesthetic data to `mocks/vibes.ts`
2. Add corresponding items to `mocks/items.ts`
3. Add a matching playlist to `mocks/playlists.ts`

### Styling

The app uses NativeWind (Tailwind CSS for React Native). Custom colors are defined in `tailwind.config.js`.
