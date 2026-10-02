import { Routes } from '@angular/router';
import { CharacterLabPage } from './pages/character-lab.page';
import { ImportDataPage } from './pages/import-data.page';
import { OverviewPage } from './pages/overview.page';
import { PlaceholderPage } from './pages/placeholder.page';
import { PredictionsPage } from './pages/predictions.page';
import { VideoLibraryPage } from './pages/video-library.page';
import { VideoDetailPage } from './pages/video-detail.page';
import { ReachFurtherResearchPage } from './pages/reach-further-research.page';
import { RenderDashboardPage } from './pages/render-dashboard.page';
import { MetaConnectionPage } from './pages/meta-connection.page';
import { MetaReelsPage } from './pages/meta-reels.page';
import { MetaReelAnalyticsPage } from './pages/meta-reel-analytics.page';

export const routes: Routes = [
  { path: 'overview', component: OverviewPage, title: 'Overview · Pompom CI' },
  { path: 'render', component: RenderDashboardPage, title: 'Render Pipeline · Pompom CI' },
  { path: 'videos', component: VideoLibraryPage, title: 'Video Library · Pompom CI' },
  { path: 'videos/detail', component: VideoDetailPage, title: 'Video Review Studio · Pompom CI' },
  { path: 'videos/:id', component: VideoDetailPage, title: 'Video Detail · Pompom CI' },
  { path: 'characters', component: CharacterLabPage, title: 'Character Lab · Pompom CI' },
  { path: 'predictions', component: PredictionsPage, title: 'Predictions · Pompom CI' },
  { path: 'import', component: ImportDataPage, title: 'Import Data · Pompom CI' },
  { path: 'experiments', component: PlaceholderPage, data: { title: 'Experiments', eyebrow: 'RESEARCH PROGRAM', copy: 'This view will list persisted experiment records when its data connection is enabled.' } },
  { path: 'test-planner', component: PlaceholderPage, data: { title: 'Test Planner', eyebrow: 'QUEUE DESIGN', copy: 'This view will use registered hypotheses and imported baseline observations.' } },
  { path: 'performance', component: PlaceholderPage, data: { title: 'Performance', eyebrow: 'OBSERVED OUTCOMES', copy: 'Import platform exports to create timestamped performance observations.' } },
  { path: 'reliability', component: PlaceholderPage, data: { title: 'Model Reliability', eyebrow: 'CALIBRATION', copy: 'Reliability statistics require locked predictions with observed outcomes.' } },
  { path: 'research', component: ReachFurtherResearchPage, title: 'Reach Further Research · Pompom CI' },
  { path: 'meta/connection', component: MetaConnectionPage, title: 'Meta Connection · Pompom CI' },
  { path: 'meta/reels', component: MetaReelsPage, title: 'Instagram Reels · Pompom CI' },
  { path: 'meta/reels/:mediaId', component: MetaReelAnalyticsPage, title: 'Reel Analytics · Pompom CI' },
  { path: 'models', component: PlaceholderPage, data: { title: 'Model Versions', eyebrow: 'MODEL REGISTRY', copy: 'This view will display persisted model registry records only.' } },
  { path: 'settings', component: PlaceholderPage, data: { title: 'Settings', eyebrow: 'WORKSPACE CONTROL', copy: 'Workspace defaults inherit the Pompom production profile. No local overrides are configured.' } },
  { path: '', pathMatch: 'full', redirectTo: 'overview' },
  { path: '**', redirectTo: 'overview' },
];
