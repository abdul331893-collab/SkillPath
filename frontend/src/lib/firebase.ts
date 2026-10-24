import { initializeApp, getApps, getApp, FirebaseApp } from "firebase/app";
import { getAuth, Auth } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID,
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID,
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
