import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

interface NavigationItem {
  label: string;
  icon: string;
  route: string;
}

@Component({
  selector: 'app-root',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly navOpen = signal(false);
  protected readonly navigation: NavigationItem[] = [
    { label: 'Overview', icon: 'OV', route: '/overview' },
    { label: 'Video Library', icon: 'VL', route: '/videos' },
    { label: 'Characters', icon: 'CH', route: '/characters' },
    { label: 'Prompt Quality', icon: 'PQ', route: '/quality' },
    { label: 'Experiments', icon: 'EX', route: '/experiments' },
    { label: 'Test Planner', icon: 'TP', route: '/test-planner' },
    { label: 'Predictions', icon: 'PR', route: '/predictions' },
    { label: 'Performance', icon: 'PF', route: '/performance' },
    { label: 'Import Data', icon: 'IM', route: '/import' },
    { label: 'Model Reliability', icon: 'MR', route: '/reliability' },
    { label: 'Reach Further', icon: 'RF', route: '/research' },
    { label: 'Meta Analytics', icon: 'MA', route: '/meta/connection' },
    { label: 'Model Versions', icon: 'MV', route: '/models' },
    { label: 'Settings', icon: 'ST', route: '/settings' },
  ];

  protected closeNavigation(): void {
    this.navOpen.set(false);
  }
}
