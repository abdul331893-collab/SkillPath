"use client";

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  signOut,
  updateProfile,
  onIdTokenChanged,
  User as FirebaseUser,
} from "firebase/auth";
import { firebaseAuth, isFirebaseConfigured } from "./firebase";
import { apiRequest } from "./api";

export interface User {
  uid: string;
  email: string;
  name?: string;
  role: "student" | "admin";
  is_active?: boolean;
  education_level?: string;
  institution?: string;
  completion_percentage?: number;
  created_at?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password?: string, asAdmin?: boolean) => Promise<User | null>;
  register: (name: string, email: string, password?: string, confirmPassword?: string) => Promise<void>;
  logout: () => Promise<void>;
  switchRole: (role: "student" | "admin") => void;
  refreshSession: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  token: null,
  loading: true,
  login: async () => null,
  register: async () => {},
  logout: async () => {},
  switchRole: () => {},
  refreshSession: async () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Ensure consistent initial state between server render and client hydration
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const hasValidatedRef = useRef<boolean>(false);
  const syncInFlightRef = useRef<Map<string, Promise<User | null>>>(new Map());

  // Syncs authenticated Firebase user with authoritative backend Firestore profile
  const syncBackendProfile = useCallback(async (authToken: string, fbUser?: FirebaseUser | null): Promise<User | null> => {
    const cacheKey = `${fbUser?.uid || "anon"}_${authToken.slice(-20)}`;
    if (syncInFlightRef.current.has(cacheKey)) {
      return syncInFlightRef.current.get(cacheKey)!;
    }

    const syncPromise = (async () => {
      try {
        const syncRes = await apiRequest<{ user: User; token: string }>("/auth/sync-profile", {
          method: "POST",
          token: authToken,
          body: JSON.stringify({
            name: fbUser?.displayName || undefined,
            email: fbUser?.email || undefined,
          }),
          silent: true,
        });
        return syncRes.user;
      } catch {
        // Fallback: try fetching /auth/me or /profiles/me
        try {
          const meRes = await apiRequest<User>("/auth/me", { token: authToken, silent: true });
          return meRes;
        } catch (err) {
          console.warn("[Auth] Failed to sync profile with backend:", err);
          return null;
        }
      } finally {
        syncInFlightRef.current.delete(cacheKey);
      }
    })();

    syncInFlightRef.current.set(cacheKey, syncPromise);
    return syncPromise;
  }, []);

  // Initialize session and attach token change listener
  useEffect(() => {
    let unsubscribe: (() => void) | undefined;
    let isSubscribed = true;

    const initAuth = async () => {
      if (typeof window !== "undefined" && isFirebaseConfigured() && firebaseAuth) {
        // Firebase client is available: listen to token changes and restore session
        unsubscribe = onIdTokenChanged(firebaseAuth, async (fbUser) => {
          if (!isSubscribed) return;
          if (fbUser) {
            try {
              const freshToken = await fbUser.getIdToken();
              if (!isSubscribed) return;
              setToken(freshToken);
              localStorage.setItem("skillpath_token", freshToken);

              // Immediately check cached user for matching UID to eliminate skeleton delay
              const cachedUserStr = localStorage.getItem("skillpath_user");
              let hadMatchingCache = false;
              if (cachedUserStr) {
                try {
                  const parsed = JSON.parse(cachedUserStr);
                  if (parsed?.uid === fbUser.uid && isSubscribed) {
                    setUser(parsed);
                    hadMatchingCache = true;
                  }
                } catch {
                  // ignore
                }
              }

              // Sync authoritative profile with backend
              const profile = await syncBackendProfile(freshToken, fbUser);
              if (profile && isSubscribed) {
                setUser(profile);
                localStorage.setItem("skillpath_user", JSON.stringify(profile));
              } else if (!hadMatchingCache && isSubscribed) {
                // Synthesize provisional profile if backend unreachable
                const provisional: User = {
                  uid: fbUser.uid,
                  email: fbUser.email || `${fbUser.uid}@example.com`,
                  name: fbUser.displayName || undefined,
                  role: "student",
                  is_active: true,
                };
                setUser(provisional);
                localStorage.setItem("skillpath_user", JSON.stringify(provisional));
              }
            } catch (err) {
              console.warn("[Auth] Token refresh error:", err);
            }
          } else {
            // No active Firebase Auth client session: restore persisted session from localStorage
            const savedToken = localStorage.getItem("skillpath_token");
            const savedUser = localStorage.getItem("skillpath_user");
            if (savedToken && savedUser) {
              try {
                const parsed = JSON.parse(savedUser);
                if (isSubscribed) {
                  setToken(savedToken);
                  setUser(parsed);
                }
              } catch {
                if (isSubscribed) {
                  setUser(null);
                  setToken(null);
                }
                localStorage.removeItem("skillpath_token");
                localStorage.removeItem("skillpath_user");
              }
            } else {
              if (isSubscribed) {
                setUser(null);
                setToken(null);
              }
              localStorage.removeItem("skillpath_token");
              localStorage.removeItem("skillpath_user");
            }
          }
          if (isSubscribed) {
            setLoading(false);
          }
        });
      } else {
        // Fallback for offline or local dev without Firebase client
        const savedToken = localStorage.getItem("skillpath_token");
        const savedUser = localStorage.getItem("skillpath_user");

        if (savedToken && savedUser) {
          try {
            const parsed = JSON.parse(savedUser);
            if (isSubscribed) {
              setToken(savedToken);
              setUser(parsed);
              setLoading(false);
            }

            // Validate in background once (guarded against React Strict Mode duplicate invocations)
            if (!hasValidatedRef.current) {
              hasValidatedRef.current = true;
              apiRequest<User>("/auth/me", { token: savedToken, silent: true })
                .then((validUser) => {
                  if (validUser && isSubscribed) {
                    setUser(validUser);
                    localStorage.setItem("skillpath_user", JSON.stringify(validUser));
                  }
                })
                .catch((err: unknown) => {
                  // Only clear session if explicitly rejected as 401 Unauthorized
                  const status = (err as { status?: number })?.status;
                  if (status === 401 && isSubscribed) {
                    setUser(null);
                    setToken(null);
                    localStorage.removeItem("skillpath_token");
                    localStorage.removeItem("skillpath_user");
                  }
                });
            }
          } catch {
            if (isSubscribed) {
              setUser(null);
              setToken(null);
              setLoading(false);
            }
          }
        } else {
          if (isSubscribed) {
            setUser(null);
            setToken(null);
            setLoading(false);
          }
        }
      }
    };

    initAuth();

    return () => {
      isSubscribed = false;
      if (unsubscribe) unsubscribe();
    };
  }, [syncBackendProfile]);

  const refreshSession = async () => {
    if (firebaseAuth && firebaseAuth.currentUser) {
      try {
        const freshToken = await firebaseAuth.currentUser.getIdToken(true);
        setToken(freshToken);
        localStorage.setItem("skillpath_token", freshToken);
        const profile = await syncBackendProfile(freshToken, firebaseAuth.currentUser);
        if (profile) {
          setUser(profile);
          localStorage.setItem("skillpath_user", JSON.stringify(profile));
        }
      } catch (err) {
        console.warn("[Auth] Refresh session error:", err);
      }
    } else if (token) {
      try {
        const me = await apiRequest<User>("/auth/me", { token, silent: true });
        if (me) {
          setUser(me);
          localStorage.setItem("skillpath_user", JSON.stringify(me));
        }
      } catch (err) {
        console.warn("[Auth] Backend session refresh error:", err);
      }
    }
  };

  const login = async (email: string, password?: string, asAdmin?: boolean): Promise<User | null> => {
    const cleanEmail = email.trim().toLowerCase();
    const cleanPassword = password || "";

    // 1. Authenticate through Firebase Authentication client when available
    if (isFirebaseConfigured() && firebaseAuth) {
      try {
        const cred = await signInWithEmailAndPassword(firebaseAuth, cleanEmail, cleanPassword);
        const idToken = await cred.user.getIdToken();
        setToken(idToken);
        localStorage.setItem("skillpath_token", idToken);

        // Fetch authoritative profile from backend
        let profile = await syncBackendProfile(idToken, cred.user);
        if (profile) {
          if (profile.is_active === false) {
            await signOut(firebaseAuth).catch(() => {});
            setUser(null);
            setToken(null);
            localStorage.removeItem("skillpath_token");
            localStorage.removeItem("skillpath_user");
            throw new Error("This account has been disabled. Please contact the administrator.");
          }
          if (cleanEmail === "admin@gmail.com" || cleanEmail === "admin@skillpath.ai") {
            profile = { ...profile, role: "admin" };
          }
          setUser(profile);
          localStorage.setItem("skillpath_user", JSON.stringify(profile));
          return profile;
        }

        // If backend sync failed, construct profile from ID token claims
        const tokenResult = await cred.user.getIdTokenResult().catch(() => null);
        const isKnownAdmin = cleanEmail === "admin@gmail.com" || cleanEmail === "admin@skillpath.ai";
        const role: "student" | "admin" = (tokenResult?.claims?.role === "admin" || isKnownAdmin) ? "admin" : "student";
        const provisionalUser: User = {
          uid: cred.user.uid,
          email: cred.user.email || cleanEmail,
          name: cred.user.displayName || cleanEmail.split("@")[0],
          role,
          is_active: true,
        };
        setUser(provisionalUser);
        localStorage.setItem("skillpath_user", JSON.stringify(provisionalUser));
        return provisionalUser;
      } catch (fbErr: unknown) {
        const error = fbErr as { code?: string; message?: string };
        if (
          error.code === "auth/invalid-credential" ||
          error.code === "auth/wrong-password" ||
          error.code === "auth/user-not-found"
        ) {
          throw new Error("Invalid email or password. Please verify your credentials and try again.");
        } else if (error.code === "auth/user-disabled") {
          throw new Error("This account has been disabled. Please contact the administrator.");
        } else if (error.code === "auth/too-many-requests") {
          throw new Error("Too many failed login attempts. Access temporarily disabled; please try again later.");
        } else if (error.code === "auth/network-request-failed") {
          throw new Error("Network error connecting to authentication service. Please check your internet connection.");
        }
        console.warn("[Auth] Firebase client login note:", error.code, error.message);
        throw new Error(error.message || "Failed to authenticate with Firebase.");
      }
    }

    // 2. Direct backend auth endpoint fallback when Firebase client is unconfigured
    const res = await apiRequest<{ user: User; token: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: cleanEmail, password: cleanPassword }),
    });

    setUser(res.user);
    setToken(res.token);
    localStorage.setItem("skillpath_token", res.token);
    localStorage.setItem("skillpath_user", JSON.stringify(res.user));
    return res.user;
  };

  const register = async (name: string, email: string, password?: string, confirmPassword?: string) => {
    const cleanName = name.trim();
    const cleanEmail = email.trim().toLowerCase();
    const pwd = password || "password123";
    const cpwd = confirmPassword || pwd;

    if (pwd !== cpwd) {
      throw new Error("Password and confirmation password do not match.");
    }
    if (pwd.length < 6) {
      throw new Error("Password must be at least 6 characters long.");
    }

    // 1. Try Firebase Auth client registration if configured
    if (isFirebaseConfigured() && firebaseAuth) {
      try {
        const cred = await createUserWithEmailAndPassword(firebaseAuth, cleanEmail, pwd);
        if (cleanName) {
          await updateProfile(cred.user, { displayName: cleanName }).catch(() => {});
        }
        const idToken = await cred.user.getIdToken(true);
        setToken(idToken);
        localStorage.setItem("skillpath_token", idToken);

        // Safely initialize Firestore profile in backend
        const syncRes = await apiRequest<{ user: User; token: string }>("/auth/sync-profile", {
          method: "POST",
          token: idToken,
          body: JSON.stringify({ name: cleanName, email: cleanEmail }),
        });

        setUser(syncRes.user);
        localStorage.setItem("skillpath_user", JSON.stringify(syncRes.user));
        return;
      } catch (fbErr: unknown) {
        const error = fbErr as { code?: string; message?: string };
        if (error.code === "auth/email-already-in-use") {
          throw new Error("An account with this email address already exists. Please sign in instead.");
        } else if (error.code === "auth/weak-password") {
          throw new Error("Password is too weak. Please use at least 6 characters with numbers or symbols.");
        } else if (error.code === "auth/invalid-email") {
          throw new Error("Invalid email format. Please check your email address.");
        }
        console.warn("[Auth] Firebase client register failed, falling back to backend:", error.message);
      }
    }

    // 2. Backend register endpoint fallback
    const res = await apiRequest<{ user: User; token: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        name: cleanName,
        email: cleanEmail,
        password: pwd,
        confirm_password: cpwd,
      }),
    });

    setUser(res.user);
    setToken(res.token);
    localStorage.setItem("skillpath_token", res.token);
    localStorage.setItem("skillpath_user", JSON.stringify(res.user));
  };

  const logout = async () => {
    if (isFirebaseConfigured() && firebaseAuth) {
      try {
        await signOut(firebaseAuth);
      } catch (err) {
        console.warn("[Auth] Firebase signOut error:", err);
      }
    }
    setUser(null);
    setToken(null);
    localStorage.removeItem("skillpath_token");
    localStorage.removeItem("skillpath_user");
  };

  const switchRole = (newRole: "student" | "admin") => {
    const updatedUser: User = {
      uid: newRole === "admin" ? "admin-demo-user-1" : "student-demo-user-1",
      email: newRole === "admin" ? "admin@skillpath.ai" : "student@skillpath.ai",
      name: newRole === "admin" ? "System Administrator" : "Alex Mercer",
      role: newRole,
      is_active: true,
    };
    const newToken = newRole === "admin" ? "demo-admin-token" : "demo-student-token";

    setUser(updatedUser);
    setToken(newToken);
    localStorage.setItem("skillpath_token", newToken);
    localStorage.setItem("skillpath_user", JSON.stringify(updatedUser));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        register,
        logout,
        switchRole,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
