/**
 * Spotify integration: OAuth (Authorization Code + PKCE) and "Save playlist
 * to my Spotify library".
 *
 * Why imperative instead of `useAuthRequest`:
 *
 * The hook-based expo-auth-session API requires the prompt to be triggered
 * from a component render, which makes a "tap a button -> get a Promise<ok>"
 * UX awkward. We do PKCE ourselves with `WebBrowser.openAuthSessionAsync`
 * so the save action stays a one-shot async function.
 *
 * Setup required (one-time, see PLAN.md):
 *
 *   1. In the Spotify developer dashboard, add the redirect URI printed by
 *      `console.log("[spotify] redirect_uri =", ...)` on first sign-in
 *      attempt -- it'll be `vibecheck://oauth-callback`.
 *   2. Set `EXPO_PUBLIC_SPOTIFY_CLIENT_ID` in `mobile/.env`.
 *   3. The mobile app must use a custom scheme (`vibecheck://`), already
 *      declared in `app.json`.
 *
 * Token is kept in-memory only -- it expires in 1h and re-auth is a one-tap
 * flow, so persistence isn't worth the AsyncStorage dependency for a demo.
 */

import * as AuthSession from "expo-auth-session";
import * as Crypto from "expo-crypto";
import * as WebBrowser from "expo-web-browser";
import type { Playlist } from "./types";

const SPOTIFY_CLIENT_ID =
  process.env.EXPO_PUBLIC_SPOTIFY_CLIENT_ID || "";

const SCOPES = [
  "playlist-modify-private",
  "playlist-modify-public",
  "user-read-private",
];

const AUTH_ENDPOINT = "https://accounts.spotify.com/authorize";
const TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token";
const API_BASE = "https://api.spotify.com/v1";

let cachedToken: { accessToken: string; expiresAt: number } | null = null;
let cachedUserId: string | null = null;

WebBrowser.maybeCompleteAuthSession();

function getRedirectUri(): string {
  // makeRedirectUri returns a `vibecheck://oauth-callback` URI in standalone /
  // dev-client builds, and an `exp://...` URL inside Expo Go. The latter must
  // also be added to the Spotify dashboard as a separate redirect URI for the
  // initial dev experience to work.
  return AuthSession.makeRedirectUri({
    scheme: "vibecheck",
    path: "oauth-callback",
  });
}

function base64UrlFromBase64(b64: string): string {
  return b64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomCodeVerifier(): string {
  // 96 chars of [A-Za-z0-9-_] - well within the 43-128 range PKCE requires.
  const bytes = Crypto.getRandomBytes(72);
  let bin = "";
  for (let i = 0; i < bytes.length; i += 1) {
    bin += String.fromCharCode(bytes[i]);
  }
  // global.btoa exists in Hermes / modern RN runtimes.
  return base64UrlFromBase64(btoa(bin));
}

async function pkceChallenge(verifier: string): Promise<string> {
  const sha = await Crypto.digestStringAsync(
    Crypto.CryptoDigestAlgorithm.SHA256,
    verifier,
    { encoding: Crypto.CryptoEncoding.BASE64 }
  );
  return base64UrlFromBase64(sha);
}

function encodeForm(params: Record<string, string>): string {
  return Object.entries(params)
    .map(
      ([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`
    )
    .join("&");
}

export interface SpotifyAuthError {
  ok: false;
  error: string;
}

export interface SpotifySaveSuccess {
  ok: true;
  playlistId: string;
  playlistUrl?: string;
  addedTracks: number;
  skippedTracks: number;
}

export type SpotifySaveResult = SpotifySaveSuccess | SpotifyAuthError;

async function fetchToken(verifier: string, code: string, redirectUri: string) {
  const resp = await fetch(TOKEN_ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: encodeForm({
      grant_type: "authorization_code",
      code,
      redirect_uri: redirectUri,
      client_id: SPOTIFY_CLIENT_ID,
      code_verifier: verifier,
    }),
  });
  if (!resp.ok) {
    const text = await resp.text().catch(() => "");
    throw new Error(`Spotify token exchange failed: ${resp.status} ${text}`);
  }
  const data = await resp.json();
  return {
    accessToken: data.access_token as string,
    expiresAt: Date.now() + (data.expires_in ?? 3600) * 1000 - 30_000,
  };
}

async function signIn(): Promise<string> {
  if (!SPOTIFY_CLIENT_ID) {
    throw new Error(
      "EXPO_PUBLIC_SPOTIFY_CLIENT_ID is not set in mobile/.env"
    );
  }
  if (cachedToken && cachedToken.expiresAt > Date.now()) {
    return cachedToken.accessToken;
  }

  const verifier = randomCodeVerifier();
  const challenge = await pkceChallenge(verifier);
  const redirectUri = getRedirectUri();

  // eslint-disable-next-line no-console
  console.log("[spotify] redirect_uri =", redirectUri);

  const authUrl =
    `${AUTH_ENDPOINT}?` +
    encodeForm({
      response_type: "code",
      client_id: SPOTIFY_CLIENT_ID,
      scope: SCOPES.join(" "),
      redirect_uri: redirectUri,
      code_challenge_method: "S256",
      code_challenge: challenge,
    });

  const result = await WebBrowser.openAuthSessionAsync(authUrl, redirectUri);
  if (result.type !== "success" || !result.url) {
    throw new Error(
      `Sign-in was ${result.type === "cancel" ? "cancelled" : "interrupted"}.`
    );
  }

  const callbackUrl = result.url;
  const search = callbackUrl.includes("?")
    ? callbackUrl.slice(callbackUrl.indexOf("?") + 1)
    : "";
  const params: Record<string, string> = {};
  for (const pair of search.split("&")) {
    const [k, v] = pair.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v ?? "");
  }
  if (params.error) {
    throw new Error(`Spotify error: ${params.error}`);
  }
  if (!params.code) {
    throw new Error("Spotify did not return an auth code.");
  }

  const token = await fetchToken(verifier, params.code, redirectUri);
  cachedToken = token;
  cachedUserId = null; // will be fetched lazily
  return token.accessToken;
}

async function spotifyFetch(
  path: string,
  init: RequestInit & { token: string }
): Promise<Response> {
  const { token, headers, ...rest } = init;
  return fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      ...(headers ?? {}),
      Authorization: `Bearer ${token}`,
    },
  });
}

async function getUserId(token: string): Promise<string> {
  if (cachedUserId) return cachedUserId;
  const resp = await spotifyFetch("/me", { method: "GET", token });
  if (!resp.ok) {
    throw new Error(`/me failed: ${resp.status}`);
  }
  const data = await resp.json();
  cachedUserId = data.id;
  return data.id;
}

async function savePlaylistToLibrary(
  playlist: Playlist
): Promise<SpotifySaveResult> {
  try {
    const token = await signIn();
    const userId = await getUserId(token);

    const trackIds = playlist.tracks
      .map((t) => t.id)
      .filter((id): id is string => Boolean(id));
    if (trackIds.length === 0) {
      return { ok: false, error: "Playlist has no Spotify tracks to save." };
    }

    const createResp = await spotifyFetch(`/users/${userId}/playlists`, {
      method: "POST",
      token,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: playlist.name,
        description: `Generated by VibeCheck for the ${playlist.aesthetic} aesthetic.`,
        public: false,
      }),
    });
    if (!createResp.ok) {
      const text = await createResp.text().catch(() => "");
      return {
        ok: false,
        error: `Create playlist failed: ${createResp.status} ${text.slice(0, 200)}`,
      };
    }
    const created = await createResp.json();
    const playlistId: string = created.id;
    const playlistUrl: string | undefined = created.external_urls?.spotify;

    // Spotify caps /tracks at 100 URIs per call.
    let added = 0;
    for (let i = 0; i < trackIds.length; i += 100) {
      const chunk = trackIds.slice(i, i + 100);
      const uris = chunk.map((id) => `spotify:track:${id}`);
      const addResp = await spotifyFetch(`/playlists/${playlistId}/tracks`, {
        method: "POST",
        token,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ uris }),
      });
      if (!addResp.ok) {
        const text = await addResp.text().catch(() => "");
        return {
          ok: false,
          error: `Add tracks failed: ${addResp.status} ${text.slice(0, 200)}`,
        };
      }
      added += chunk.length;
    }

    return {
      ok: true,
      playlistId,
      playlistUrl,
      addedTracks: added,
      skippedTracks: playlist.tracks.length - added,
    };
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

function signOut(): void {
  cachedToken = null;
  cachedUserId = null;
}

export const spotifyApi = {
  signIn,
  signOut,
  savePlaylistToLibrary,
};
