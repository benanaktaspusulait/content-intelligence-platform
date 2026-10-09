import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import {
  MetaConnection,
  MetaPageContent,
  MetaPageInsights,
  MetaReelAnalytics,
  MetaReelsPage,
  MetaReelSummary,
  MetaSnapshotResult,
  MetaComment,
} from './meta-read.models';

/** Read-only client for the Meta analytics API. All reads are GET; snapshots are append-only. */
@Injectable({ providedIn: 'root' })
export class MetaReadService {
  private readonly baseUrl = '/api/v1/meta';

  constructor(private readonly http: HttpClient) {}

  getConnection(): Observable<MetaConnection> {
    return this.http.get<MetaConnection>(`${this.baseUrl}/connection`);
  }

  getPageContent(): Observable<MetaPageContent> {
    return this.http.get<MetaPageContent>(`${this.baseUrl}/page/content`);
  }

  getPageInsights(objectId?: string | null): Observable<MetaPageInsights> {
    const suffix = objectId ? `/${encodeURIComponent(objectId)}` : '';
    return this.http.get<MetaPageInsights>(`${this.baseUrl}/page/insights${suffix}`);
  }

  listReels(after?: string | null, limit = 25): Observable<MetaReelsPage> {
    let params = new HttpParams().set('limit', String(limit));
    if (after) {
      params = params.set('after', after);
    }
    return this.http.get<MetaReelsPage>(`${this.baseUrl}/instagram/reels`, { params });
  }

  getReel(mediaId: string): Observable<MetaReelSummary> {
    return this.http.get<MetaReelSummary>(`${this.baseUrl}/instagram/reels/${mediaId}`);
  }

  getAnalytics(mediaId: string): Observable<MetaReelAnalytics> {
    return this.http.get<MetaReelAnalytics>(`${this.baseUrl}/instagram/reels/${mediaId}/analytics`);
  }

  captureSnapshot(mediaId: string): Observable<MetaSnapshotResult> {
    return this.http.post<MetaSnapshotResult>(
      `${this.baseUrl}/instagram/reels/${mediaId}/snapshots`,
      {},
    );
  }

  listComments(): Observable<MetaComment[]> { return this.http.get<MetaComment[]>(`${this.baseUrl}/comments`); }
  createCommentDraft(commentId: string, draftText: string): Observable<unknown> {
    return this.http.post(`${this.baseUrl}/comments/${commentId}/replies/draft`, { draftText, idempotencyKey: crypto.randomUUID() });
  }
  submitCommentReply(replyId: string): Observable<unknown> { return this.http.post(`${this.baseUrl}/comments/replies/${replyId}/submit`, {}); }
  approveCommentReply(replyId: string, reviewer: string): Observable<unknown> { return this.http.post(`${this.baseUrl}/comments/replies/${replyId}/approve`, { reviewer }); }
  rejectCommentReply(replyId: string, reviewer: string, reason: string): Observable<unknown> { return this.http.post(`${this.baseUrl}/comments/replies/${replyId}/reject`, { reviewer, reason }); }
  sendCommentReply(replyId: string): Observable<unknown> { return this.http.post(`${this.baseUrl}/comments/replies/${replyId}/send`, {}); }
  getOperationsStatus(): Observable<{ health: string; commentReplyEnabled: boolean; commentCount: number; pendingWebhookCount: number }> {
    return this.http.get<{ health: string; commentReplyEnabled: boolean; commentCount: number; pendingWebhookCount: number }>(`${this.baseUrl}/operations/status`);
  }
  reconcileComments(limit = 100): Observable<{ processed: number }> {
    return this.http.post<{ processed: number }>(`${this.baseUrl}/comments/reconcile`, {}, { params: new HttpParams().set('limit', String(limit)) });
  }
}
