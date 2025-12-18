/*
  App frontend configuration placeholders
  Replace the %%TOKENS%% during deployment or build as needed.
*/

window.APP_CONFIG = {
  // Core
  apiBaseUrl: "%%API_BASE_URL%%",      // e.g., http://127.0.0.1:5000
  environment: "%%ENVIRONMENT%%",      // e.g., development|staging|production
  defaultLanguage: "%%LANGUAGE%%",     // e.g., pt|en|es|fr

  // UI
  ui: {
    theme: "%%THEME%%",                // e.g., light|dark|system
    notifications: {
      enabled: "%%NOTIFICATIONS_ENABLED%%", // true|false
      durationMs: "%%NOTIFY_DURATION_MS%%"   // e.g., 5000
    }
  },

  // Server (DICOM)
  server: {
    aet: "%%SERVER_AET%%",
    host: "%%SERVER_HOST%%",
    port: "%%SERVER_PORT%%",
    clientAet: "%%CLIENT_AET%%"
  },

  // Database (non-sensitive placeholders only)
  database: {
    type: "%%DB_TYPE%%",               // oracle|postgres|mysql
    dsn: "%%DB_DSN%%"                  // e.g., 127.0.0.1:1521/ORCLCDB
  }
};
