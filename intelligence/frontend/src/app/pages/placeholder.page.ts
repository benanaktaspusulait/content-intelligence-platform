import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';

@Component({
  selector: 'app-placeholder-page',
  imports: [RouterLink],
  template: `
    <header class="page-header"><div><span class="eyebrow">{{ eyebrow }}</span><h1>{{ title }}</h1><p>Operational records and current evidence state.</p></div></header>
    <section class="empty-workspace"><div class="empty-signal" aria-hidden="true"><i></i><i></i><i></i><i></i><span>0</span></div><span class="eyebrow">CURRENT STATE</span><h2>Nothing qualified yet</h2><p>{{ copy }}</p><a class="button button--secondary" routerLink="/overview">Return to overview</a></section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PlaceholderPage {
  private readonly data = inject(ActivatedRoute).snapshot.data;
  protected readonly title = this.data['title'] as string;
  protected readonly eyebrow = this.data['eyebrow'] as string;
  protected readonly copy = this.data['copy'] as string;
}
