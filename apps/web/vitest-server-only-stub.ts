// Stub for 'server-only' package in Vitest test environments.
// The real package throws at runtime if imported in a client context;
// in tests we just allow the import silently.
export {};
