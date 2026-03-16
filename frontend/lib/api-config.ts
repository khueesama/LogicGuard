/**
 * API Configuration Utility
 * Automatically detects the appropriate API URL based on environment
 */

/**
 * Get the API base URL
 * Priority:
 * 1. NEXT_PUBLIC_API_URL environment variable
 * 2. Auto-detect based on window.location (for browser)
 * 3. Fallback to localhost
 */
export function getApiBaseUrl(): string {
  // 1. ƯU TIÊN SỐ 1: Biến môi trường (Dành cho Vercel/Production)
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL
  }

  // 2. Dự phòng cho Local Development
  if (typeof window !== "undefined") {
    const { hostname } = window.location
    if (hostname === "localhost" || hostname === "127.0.0.1") {
      return "http://localhost:8000/api"
    }
  }

  // 3. Mặc định cuối cùng
  return "http://localhost:8000/api"
}

/**
 * Get base URL without /api suffix (for special endpoints)
 */
export function getApiBaseUrlWithoutSuffix(): string {
  const fullUrl = getApiBaseUrl()
  return fullUrl.replace(/\/api$/, "")
}

/**
 * Check if running in production
 */
export function isProduction(): boolean {
  return process.env.NODE_ENV === "production"
}

/**
 * Check if running in development
 */
export function isDevelopment(): boolean {
  return process.env.NODE_ENV === "development"
}

/**
 * Get the current host information
 */
export function getHostInfo() {
  if (typeof window === "undefined") {
    return {
      hostname: "server",
      protocol: "http:",
      isLocal: false,
    }
  }

  const { hostname, protocol } = window.location
  const isLocal = hostname === "localhost" || hostname === "127.0.0.1"

  return {
    hostname,
    protocol,
    isLocal,
  }
}
