import { Routes } from '@angular/router';
import { CharacterLabPage } from './pages/character-lab.page';
import { ImportDataPage } from './pages/import-data.page';
import { OverviewPage } from './pages/overview.page';
import { PredictionsPage } from './pages/predictions.page';
import { VideoLibraryPage } from './pages/video-library.page';
import { VideoDetailPage } from './pages/video-detail.page';
import { VideoAnalysisWorkbenchPage } from './pages/video-analysis-workbench.page';
import { ReachFurtherResearchPage } from './pages/reach-further-research.page';
import { RenderDashboardPage } from './pages/render-dashboard.page';
import { MetaConnectionPage } from './pages/meta-connection.page';
import { MetaReelsPage } from './pages/meta-reels.page';
import { MetaReelAnalyticsPage } from './pages/meta-reel-analytics.page';
import { QualityValidatorComponent } from './pages/quality-validator/quality-validator.component';
import { RuleGovernancePage } from './pages/rule-governance.page';
import { ExperimentsPage } from './pages/experiments.page';
import { TestPlannerPage } from './pages/test-planner.page';
import { ModelsPage } from './pages/models.page';
import { PerformancePage } from './pages/performance.page';
import { ReliabilityPage } from './pages/reliability.page';
import { OperationsPage } from './pages/operations.page';

export const routes: Routes = [
  { path: 'overview', component: OverviewPage, title: 'Overview · Pompom CI' },
  { path: 'render', component: RenderDashboardPage, title: 'Render Pipeline · Pompom CI' },
  { path: 'rule-governance', component: RuleGovernancePage, title: 'Rule Governance · Pompom CI' },
  { path: 'quality', component: QualityValidatorComponent, title: 'Prompt Quality · Pompom CI' },
  { path: 'videos', component: VideoLibraryPage, title: 'Video Library · Pompom CI' },
  { path: 'videos/workbench', component: VideoAnalysisWorkbenchPage, title: 'Analysis Workbench · Pompom CI' },
  { path: 'videos/detail', component: VideoDetailPage, title: 'Video Review Studio · Pompom CI' },
  { path: 'videos/:id', component: VideoDetailPage, title: 'Video Detail · Pompom CI' },
  { path: 'characters', component: CharacterLabPage, title: 'Character Lab · Pompom CI' },
  { path: 'predictions', component: PredictionsPage, title: 'Predictions · Pompom CI' },
  { path: 'import', component: ImportDataPage, title: 'Import Data · Pompom CI' },
  { path: 'experiments', component: ExperimentsPage, title: 'Experiments · Pompom CI' },
  { path: 'test-planner', component: TestPlannerPage, title: 'Test Planner · Pompom CI' },
  { path: 'performance', component: PerformancePage, title: 'Performance · Pompom CI' },
  { path: 'reliability', component: ReliabilityPage, title: 'Model Reliability · Pompom CI' },
  { path: 'research', component: ReachFurtherResearchPage, title: 'Reach Further Research · Pompom CI' },
  { path: 'meta/connection', component: MetaConnectionPage, title: 'Meta Connection · Pompom CI' },
  { path: 'meta/reels', component: MetaReelsPage, title: 'Instagram Reels · Pompom CI' },
  { path: 'meta/reels/:mediaId', component: MetaReelAnalyticsPage, title: 'Reel Analytics · Pompom CI' },
  { path: 'models', component: ModelsPage, title: 'Model Versions · Pompom CI' },
  { path: 'operations', component: OperationsPage, title: 'Operations · Pompom CI' },
  { path: '', pathMatch: 'full', redirectTo: 'overview' },
  { path: '**', redirectTo: 'overview' },
];
