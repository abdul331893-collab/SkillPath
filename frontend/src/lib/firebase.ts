import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import { getAuth, setPersistence, browserLocalPersistence, inMemoryPersistence, Auth } from "firebase/auth";

// Production Firebase Project skillpath-c8115 configuration
// Defaults guarantee client SDK initializes properly even if build-time env vars are absent on Render.
const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyDjhTnHLQ1NGr8r2KR7zTwcdnKdpF5oasY",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "skillpath-c8115.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "skillpath-c8115",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "skillpath-c8115.firebasestorage.app",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "554229646158",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:554229646158:web:8fe0e17df9a23ecaed541f",
};

export const isFirebaseConfigured = (): boolean => {
  return Boolean(
    firebaseConfig.apiKey &&
    firebaseConfig.projectId &&
    firebaseConfig.apiKey !== "undefined"
  );
};

let app: FirebaseApp | null = null;
let authInstance: Auth | null = null;

if (typeof window !== "undefined" && isFirebaseConfigured()) {
  try {
    app = getApps().length > 0 ? getApp() : initializeApp(firebaseConfig);
    authInstance = getAuth(app);
    // Explicitly configure browser local persistence so sessions persist across page refreshes and browser restarts
    setPersistence(authInstance, browserLocalPersistence).catch((err) => {
      console.warn("[Firebase] setPersistence browserLocalPersistence warning:", err);
    });
  } catch (err) {
    console.warn("[Firebase] Client initialization warning:", err);
  }
}

export const firebaseApp = app;
export const firebaseAuth = authInstance;

export async function getCurrentIdToken(forceRefresh = false): Promise<string | null> {
  if (!authInstance || !authInstance.currentUser) {
    return null;
  }
  try {
    return await authInstance.currentUser.getIdToken(forceRefresh);
  } catch (err) {
    console.warn("[Firebase] Failed to get ID token:", err);
    return null;
  }
}
