export const AthenaPresenceState = {
  OFFLINE: "offline",
  BOOTING: "booting",
  IDLE: "idle",
  LISTENING: "listening",
  UNDERSTANDING: "understanding",
  THINKING: "thinking",
  SPEAKING: "speaking",
  WAITING: "waiting",
  APPROVAL: "approval",
  SUCCESS: "success",
  WARNING: "warning",
  ERROR: "error",
} as const;

export type AthenaPresenceState = (typeof AthenaPresenceState)[keyof typeof AthenaPresenceState];
