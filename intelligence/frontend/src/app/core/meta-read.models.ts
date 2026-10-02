export type MetaConnectionStatus = 'CONNECTED' | 'DEGRADED' | 'UNAVAILABLE' | 'NOT_CONFIGURED';
export type MetaPageManagementVerification = 'VERIFIED' | 'NOT_VERIFIED' | 'UNAVAILABLE';
export type MetaPermissionStatus = 'AVAILABLE' | 'UNAVAILABLE' | 'NOT_REQUESTED';
export type MetaMatchStatus = 'EXACT' | 'UNMATCHED' | 'AMBIGUOUS' | 'CONFLICT';
export type MetaMatchMethod = 'PLATFORM_CONTENT_ID' | 'PERMALINK' | 'MANUAL';
export type MetaMetricAvailability = 'NOT_REQUESTED' | 'AVAILABLE' | 'PARTIAL' | 'UNAVAILABLE';

export interface MetaPermissionCheck {
  permission: string;
  status: MetaPermissionStatus;
  message: string;
}

export interface MetaConnection {
  status: MetaConnectionStatus;
  connected: boolean;
  readOnlyAnalytics: boolean;
  page: { id: string; name: string; category: string } | null;
  instagramAccount: {
    id: string;
    username: string;
    accountType: string;
    mediaCount: number | null;
    profilePictureUrl: string | null;
  } | null;
  lastValidatedAt: string | null;
  apiVersion: string;
  requiredPermissions: MetaPermissionCheck[];
  optionalPermissions: MetaPermissionCheck[];
  pageManagementVerification: MetaPageManagementVerification;
  message: string;
}

export interface MetaLocalMatch {
  status: MetaMatchStatus;
  videoId: string | null;
  publicationId: string | null;
  matchMethod: MetaMatchMethod | null;
  detail: string | null;
}

export interface MetaReelSummary {
  mediaId: string;
  mediaType: string | null;
  mediaProductType: string | null;
  caption: string | null;
  permalink: string | null;
  publishedAt: string | null;
  thumbnailUrl: string | null;
  localMatch: MetaLocalMatch;
}

export interface MetaReelsPage {
  reels: MetaReelSummary[];
  nextCursor: string | null;
  hasMore: boolean;
  apiVersion: string;
}

export interface MetaMetrics {
  views: number | null;
  reach: number | null;
  shares: number | null;
  saved: number | null;
  totalInteractions: number | null;
}

export interface MetaSnapshot {
  observationId: string | null;
  collectionRunId: string | null;
  measuredAt: string | null;
  availability: MetaMetricAvailability;
  unavailableReason: string | null;
  metrics: MetaMetrics;
}

export interface MetaReelAnalytics {
  mediaId: string;
  mediaType: string | null;
  mediaProductType: string | null;
  caption: string | null;
  permalink: string | null;
  publishedAt: string | null;
  thumbnailUrl: string | null;
  localMatch: MetaLocalMatch;
  availability: MetaMetricAvailability;
  unavailableReason: string | null;
  live: MetaMetrics;
  history: MetaSnapshot[];
  apiVersion: string;
}

export type MetaPageContentAvailability = 'AVAILABLE' | 'PARTIAL' | 'UNAVAILABLE';

export interface MetaPagePost {
  id: string;
  message: string | null;
  publishedAt: string | null;
  permalinkUrl: string | null;
}

export interface MetaPageContent {
  availability: MetaPageContentAvailability;
  unavailableReason: string | null;
  page: { id: string; name: string; category: string } | null;
  posts: MetaPagePost[];
  apiVersion: string;
}

export interface MetaSnapshotResult {
  mediaId: string;
  observationId: string | null;
  collectionRunId: string | null;
  measuredAt: string | null;
  persisted: boolean;
  localMatch: MetaLocalMatch;
  availability: MetaMetricAvailability;
  unavailableReason: string | null;
  metrics: MetaMetrics;
}
