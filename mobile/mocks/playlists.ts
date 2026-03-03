import type { Playlist, Track } from "../services/types";

export const mockPlaylists: Record<string, Playlist> = {
  cottagecore: {
    id: "pl-cottagecore",
    name: "Cottagecore Dreams",
    aesthetic: "cottagecore",
    coverImage: "https://picsum.photos/seed/cottage-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Willow",
        artist: "Taylor Swift",
        albumArt: "https://picsum.photos/seed/willow/100/100",
        durationMs: 214000,
      },
      {
        id: "t2",
        name: "Bloom",
        artist: "The Paper Kites",
        albumArt: "https://picsum.photos/seed/bloom/100/100",
        durationMs: 235000,
      },
      {
        id: "t3",
        name: "Harvest Moon",
        artist: "Neil Young",
        albumArt: "https://picsum.photos/seed/harvest/100/100",
        durationMs: 312000,
      },
      {
        id: "t4",
        name: "Northern Wind",
        artist: "City and Colour",
        albumArt: "https://picsum.photos/seed/northern/100/100",
        durationMs: 289000,
      },
      {
        id: "t5",
        name: "Sunday Morning",
        artist: "Maroon 5",
        albumArt: "https://picsum.photos/seed/sunday/100/100",
        durationMs: 295000,
      },
    ],
  },
  minimalist: {
    id: "pl-minimalist",
    name: "Minimal Mood",
    aesthetic: "minimalist",
    coverImage: "https://picsum.photos/seed/minimal-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Intro",
        artist: "The xx",
        albumArt: "https://picsum.photos/seed/intro/100/100",
        durationMs: 128000,
      },
      {
        id: "t2",
        name: "Midnight City",
        artist: "M83",
        albumArt: "https://picsum.photos/seed/midnight/100/100",
        durationMs: 243000,
      },
      {
        id: "t3",
        name: "Breathe",
        artist: "Télépopmusik",
        albumArt: "https://picsum.photos/seed/breathe/100/100",
        durationMs: 275000,
      },
      {
        id: "t4",
        name: "Teardrop",
        artist: "Massive Attack",
        albumArt: "https://picsum.photos/seed/teardrop/100/100",
        durationMs: 330000,
      },
      {
        id: "t5",
        name: "Hyperballad",
        artist: "Björk",
        albumArt: "https://picsum.photos/seed/hyperballad/100/100",
        durationMs: 302000,
      },
    ],
  },
  "dark academia": {
    id: "pl-dark-academia",
    name: "Late Night Study Session",
    aesthetic: "dark academia",
    coverImage: "https://picsum.photos/seed/darkacademia-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Clair de Lune",
        artist: "Claude Debussy",
        albumArt: "https://picsum.photos/seed/clair/100/100",
        durationMs: 302000,
      },
      {
        id: "t2",
        name: "Motion Picture Soundtrack",
        artist: "Radiohead",
        albumArt: "https://picsum.photos/seed/motion/100/100",
        durationMs: 188000,
      },
      {
        id: "t3",
        name: "First Day of My Life",
        artist: "Bright Eyes",
        albumArt: "https://picsum.photos/seed/firstday/100/100",
        durationMs: 193000,
      },
      {
        id: "t4",
        name: "Such Great Heights",
        artist: "The Postal Service",
        albumArt: "https://picsum.photos/seed/heights/100/100",
        durationMs: 269000,
      },
      {
        id: "t5",
        name: "Gymnopedie No.1",
        artist: "Erik Satie",
        albumArt: "https://picsum.photos/seed/gymnopedie/100/100",
        durationMs: 195000,
      },
    ],
  },
  "clean girl": {
    id: "pl-clean-girl",
    name: "That Girl Morning",
    aesthetic: "clean girl",
    coverImage: "https://picsum.photos/seed/cleangirl-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Golden Hour",
        artist: "JVKE",
        albumArt: "https://picsum.photos/seed/golden/100/100",
        durationMs: 210000,
      },
      {
        id: "t2",
        name: "Good Days",
        artist: "SZA",
        albumArt: "https://picsum.photos/seed/gooddays/100/100",
        durationMs: 280000,
      },
      {
        id: "t3",
        name: "Sunflower",
        artist: "Post Malone",
        albumArt: "https://picsum.photos/seed/sunflower/100/100",
        durationMs: 158000,
      },
      {
        id: "t4",
        name: "Levitating",
        artist: "Dua Lipa",
        albumArt: "https://picsum.photos/seed/levitating/100/100",
        durationMs: 203000,
      },
      {
        id: "t5",
        name: "Blinding Lights",
        artist: "The Weeknd",
        albumArt: "https://picsum.photos/seed/blinding/100/100",
        durationMs: 200000,
      },
    ],
  },
  "indie sleaze": {
    id: "pl-indie-sleaze",
    name: "2AM Cigarette Break",
    aesthetic: "indie sleaze",
    coverImage: "https://picsum.photos/seed/indiesleaze-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Last Nite",
        artist: "The Strokes",
        albumArt: "https://picsum.photos/seed/lastnite/100/100",
        durationMs: 195000,
      },
      {
        id: "t2",
        name: "Take Me Out",
        artist: "Franz Ferdinand",
        albumArt: "https://picsum.photos/seed/takemeout/100/100",
        durationMs: 237000,
      },
      {
        id: "t3",
        name: "Dance, Dance",
        artist: "Fall Out Boy",
        albumArt: "https://picsum.photos/seed/dance/100/100",
        durationMs: 183000,
      },
      {
        id: "t4",
        name: "Mr Brightside",
        artist: "The Killers",
        albumArt: "https://picsum.photos/seed/brightside/100/100",
        durationMs: 222000,
      },
      {
        id: "t5",
        name: "Reptilia",
        artist: "The Strokes",
        albumArt: "https://picsum.photos/seed/reptilia/100/100",
        durationMs: 214000,
      },
    ],
  },
  bohemian: {
    id: "pl-bohemian",
    name: "Free Spirit",
    aesthetic: "bohemian",
    coverImage: "https://picsum.photos/seed/boho-pl/400/400",
    tracks: [
      {
        id: "t1",
        name: "Dreams",
        artist: "Fleetwood Mac",
        albumArt: "https://picsum.photos/seed/dreams/100/100",
        durationMs: 254000,
      },
      {
        id: "t2",
        name: "Rhiannon",
        artist: "Fleetwood Mac",
        albumArt: "https://picsum.photos/seed/rhiannon/100/100",
        durationMs: 276000,
      },
      {
        id: "t3",
        name: "Space Oddity",
        artist: "David Bowie",
        albumArt: "https://picsum.photos/seed/space/100/100",
        durationMs: 312000,
      },
      {
        id: "t4",
        name: "Both Sides Now",
        artist: "Joni Mitchell",
        albumArt: "https://picsum.photos/seed/bothsides/100/100",
        durationMs: 287000,
      },
      {
        id: "t5",
        name: "Landslide",
        artist: "Fleetwood Mac",
        albumArt: "https://picsum.photos/seed/landslide/100/100",
        durationMs: 199000,
      },
    ],
  },
};

export function getPlaylistForAesthetic(aesthetic: string): Playlist {
  const normalizedAesthetic = aesthetic.toLowerCase();
  return mockPlaylists[normalizedAesthetic] || mockPlaylists.minimalist;
}

export function getRandomPlaylist(): Playlist {
  const aesthetics = Object.keys(mockPlaylists);
  const randomAesthetic = aesthetics[Math.floor(Math.random() * aesthetics.length)];
  return mockPlaylists[randomAesthetic];
}
