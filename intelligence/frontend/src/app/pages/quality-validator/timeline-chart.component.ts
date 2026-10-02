import { Component, Input, OnChanges } from '@angular/core';
import { CommonModule } from '@angular/common';

interface TimelineData {
  beats: Beat[];
  consequenceMarkers: ConsequenceMarker[];
  stateSegments: StateSegment[];
}

interface Beat {
  startTime: number;
  endTime: number;
  action: string;
  consequence: string;
  intensity: number;
  isNewConsequence: boolean;
}

interface ConsequenceMarker {
  time: number;
  consequence: string;
  type: string;
}

interface StateSegment {
  stateId: string;
  startTime: number;
  endTime: number;
  percentage: number;
}

@Component({
  selector: 'app-timeline-chart',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="timeline-chart" *ngIf="timelineData">
      <!-- Chart Container -->
      <svg 
        [attr.viewBox]="'0 0 ' + width + ' ' + height"
        class="timeline-svg"
        (mousemove)="onMouseMove($event)"
        (mouseleave)="hideTooltip()">
        
        <!-- Background Grid -->
        <g class="grid">
          <line *ngFor="let tick of timeTicks" 
                [attr.x1]="getX(tick)" 
                [attr.y1]="margin.top" 
                [attr.x2]="getX(tick)" 
                [attr.y2]="height - margin.bottom"
                stroke="#e9ecef" 
                stroke-width="1"/>
        </g>

        <!-- Visual State Blocks (Background) -->
        <g class="state-blocks">
          <rect *ngFor="let segment of timelineData.stateSegments; let i = index"
                [attr.x]="getX(segment.startTime)"
                [attr.y]="margin.top"
                [attr.width]="getX(segment.endTime) - getX(segment.startTime)"
                [attr.height]="chartHeight"
                [attr.fill]="getStateColor(i)"
                [attr.opacity]="segment.percentage > 0.30 ? '0.4' : '0.2'"
                [attr.stroke]="segment.percentage > 0.30 ? '#dc3545' : 'none'"
                [attr.stroke-width]="segment.percentage > 0.30 ? '2' : '0'"/>
        </g>

        <!-- Intensity Curve -->
        <g class="intensity-curve">
          <path 
            [attr.d]="intensityPath"
            fill="none"
            stroke="#007bff"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"/>
          
          <!-- Intensity Points -->
          <circle *ngFor="let beat of timelineData.beats"
                  [attr.cx]="getX((beat.startTime + beat.endTime) / 2)"
                  [attr.cy]="getY(beat.intensity)"
                  r="5"
                  [attr.fill]="getIntensityColor(beat.intensity)"
                  [attr.stroke]="'white'"
                  [attr.stroke-width]="'2'"
                  class="intensity-point"
                  (mouseenter)="showBeatTooltip(beat, $event)"
                  (mouseleave)="hideTooltip()"/>
        </g>

        <!-- Consequence Markers -->
        <g class="consequence-markers">
          <g *ngFor="let marker of timelineData.consequenceMarkers">
            <line 
              [attr.x1]="getX(marker.time)"
              [attr.y1]="margin.top"
              [attr.x2]="getX(marker.time)"
              [attr.y2]="height - margin.bottom"
              [attr.stroke]="marker.type === 'distinct' ? '#28a745' : '#6c757d'"
              [attr.stroke-width]="marker.type === 'distinct' ? '2' : '1'"
              [attr.stroke-dasharray]="marker.type === 'distinct' ? '0' : '4,4'"
              [attr.opacity]="marker.type === 'distinct' ? '0.8' : '0.4'"/>
            
            <circle *ngIf="marker.type === 'distinct'"
                    [attr.cx]="getX(marker.time)"
                    [attr.cy]="margin.top - 10"
                    r="6"
                    fill="#28a745"
                    stroke="white"
                    stroke-width="2"
                    class="consequence-point"
                    (mouseenter)="showConsequenceTooltip(marker, $event)"
                    (mouseleave)="hideTooltip()"/>
          </g>
        </g>

        <!-- Critical Threshold Line (30% rule) -->
        <line 
          x1="0"
          [attr.y1]="margin.top - 5"
          [attr.x2]="width"
          [attr.y2]="margin.top - 5"
          stroke="#ffc107"
          stroke-width="1"
          stroke-dasharray="4,4"
          opacity="0.5"/>

        <!-- X Axis -->
        <g class="x-axis">
          <line 
            [attr.x1]="margin.left"
            [attr.y1]="height - margin.bottom"
            [attr.x2]="width - margin.right"
            [attr.y2]="height - margin.bottom"
            stroke="#495057"
            stroke-width="2"/>
          
          <text *ngFor="let tick of timeTicks"
                [attr.x]="getX(tick)"
                [attr.y]="height - margin.bottom + 20"
                text-anchor="middle"
                font-size="12"
                fill="#6c757d">
            {{ tick.toFixed(1) }}s
          </text>
        </g>

        <!-- Y Axis -->
        <g class="y-axis">
          <line 
            [attr.x1]="margin.left"
            [attr.y1]="margin.top"
            [attr.x2]="margin.left"
            [attr.y2]="height - margin.bottom"
            stroke="#495057"
            stroke-width="2"/>
          
          <text *ngFor="let tick of intensityTicks"
                [attr.x]="margin.left - 10"
                [attr.y]="getY(tick)"
                text-anchor="end"
                dominant-baseline="middle"
                font-size="12"
                fill="#6c757d">
            {{ tick }}
          </text>
          
          <text 
            [attr.x]="15"
            [attr.y]="(margin.top + (height - margin.bottom)) / 2"
            text-anchor="middle"
            font-size="14"
            font-weight="600"
            fill="#2c3e50"
            [attr.transform]="'rotate(-90, 15, ' + ((margin.top + (height - margin.bottom)) / 2) + ')'">
            Intensity
          </text>
        </g>

        <!-- Legend -->
        <g class="legend" [attr.transform]="'translate(' + (width - 200) + ', 20)'">
          <rect x="0" y="0" width="15" height="15" fill="#28a745"/>
          <text x="20" y="12" font-size="11" fill="#2c3e50">New Consequence</text>
          
          <rect x="0" y="25" width="15" height="15" fill="none" stroke="#dc3545" stroke-width="2"/>
          <text x="20" y="37" font-size="11" fill="#2c3e50">Static State >30%</text>
        </g>
      </svg>

      <!-- Tooltip -->
      <div *ngIf="tooltip.visible" 
           class="timeline-tooltip"
           [style.left.px]="tooltip.x"
           [style.top.px]="tooltip.y">
        <div class="tooltip-title">{{ tooltip.title }}</div>
        <div class="tooltip-content" [innerHTML]="tooltip.content"></div>
      </div>

      <!-- Timeline Stats -->
      <div class="timeline-stats">
        <div class="stat-item">
          <span class="stat-label">Duration:</span>
          <span class="stat-value">{{ maxTime.toFixed(1) }}s</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Beats:</span>
          <span class="stat-value">{{ timelineData.beats.length }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">New Consequences:</span>
          <span class="stat-value">{{ newConsequenceCount }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">Avg Intensity:</span>
          <span class="stat-value">{{ avgIntensity.toFixed(1) }}/10</span>
        </div>
        <div class="stat-item" *ngIf="maxStatePercentage > 0.30">
          <span class="stat-label warning">⚠️ Max State:</span>
          <span class="stat-value warning">{{ (maxStatePercentage * 100).toFixed(0) }}%</span>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .timeline-chart {
      position: relative;
      background: white;
      border-radius: 8px;
      padding: 1rem;
    }

    .timeline-svg {
      width: 100%;
      height: auto;
      cursor: crosshair;
    }

    .intensity-point,
    .consequence-point {
      cursor: pointer;
      transition: r 0.2s;
    }

    .intensity-point:hover,
    .consequence-point:hover {
      r: 8;
    }

    .timeline-tooltip {
      position: absolute;
      background: rgba(0, 0, 0, 0.9);
      color: white;
      padding: 0.75rem;
      border-radius: 6px;
      pointer-events: none;
      z-index: 1000;
      max-width: 300px;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .tooltip-title {
      font-weight: 600;
      margin-bottom: 0.5rem;
      padding-bottom: 0.5rem;
      border-bottom: 1px solid rgba(255, 255, 255, 0.3);
    }

    .tooltip-content {
      font-size: 0.9rem;
      line-height: 1.4;
    }

    .timeline-stats {
      display: flex;
      justify-content: space-around;
      flex-wrap: wrap;
      gap: 1rem;
      margin-top: 1rem;
      padding: 1rem;
      background: #f8f9fa;
      border-radius: 6px;
    }

    .stat-item {
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    .stat-label {
      font-size: 0.85rem;
      color: #6c757d;
      margin-bottom: 0.25rem;

      &.warning {
        color: #dc3545;
        font-weight: 600;
      }
    }

    .stat-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: #2c3e50;

      &.warning {
        color: #dc3545;
      }
    }
  `]
})
export class TimelineChartComponent implements OnChanges {
  @Input() timelineData!: TimelineData;

  // Chart dimensions
  width = 1200;
  height = 400;
  margin = { top: 40, right: 40, bottom: 60, left: 60 };
  chartWidth = 0;
  chartHeight = 0;

  // Scales
  maxTime = 15;
  maxIntensity = 10;
  timeTicks: number[] = [];
  intensityTicks: number[] = [];

  // Data
  intensityPath = '';
  newConsequenceCount = 0;
  avgIntensity = 0;
  maxStatePercentage = 0;

  // Tooltip
  tooltip = {
    visible: false,
    x: 0,
    y: 0,
    title: '',
    content: ''
  };

  ngOnChanges(): void {
    if (!this.timelineData) return;

    this.chartWidth = this.width - this.margin.left - this.margin.right;
    this.chartHeight = this.height - this.margin.top - this.margin.bottom;

    this.calculateMetrics();
    this.generateTicks();
    this.generateIntensityPath();
  }

  calculateMetrics(): void {
    // Max time
    if (this.timelineData.beats.length > 0) {
      this.maxTime = Math.max(...this.timelineData.beats.map(b => b.endTime));
    }

    // New consequence count
    this.newConsequenceCount = this.timelineData.beats.filter(b => b.isNewConsequence).length;

    // Average intensity
    if (this.timelineData.beats.length > 0) {
      const sum = this.timelineData.beats.reduce((acc, b) => acc + b.intensity, 0);
      this.avgIntensity = sum / this.timelineData.beats.length;
    }

    // Max state percentage
    if (this.timelineData.stateSegments.length > 0) {
      this.maxStatePercentage = Math.max(...this.timelineData.stateSegments.map(s => s.percentage));
    }
  }

  generateTicks(): void {
    // Time ticks (every 2.5s)
    this.timeTicks = [];
    for (let t = 0; t <= this.maxTime; t += 2.5) {
      this.timeTicks.push(t);
    }
    if (this.timeTicks[this.timeTicks.length - 1] !== this.maxTime) {
      this.timeTicks.push(this.maxTime);
    }

    // Intensity ticks (0, 2, 4, 6, 8, 10)
    this.intensityTicks = [0, 2, 4, 6, 8, 10];
  }

  generateIntensityPath(): void {
    if (this.timelineData.beats.length === 0) {
      this.intensityPath = '';
      return;
    }

    const points = this.timelineData.beats.map(beat => {
      const x = this.getX((beat.startTime + beat.endTime) / 2);
      const y = this.getY(beat.intensity);
      return `${x},${y}`;
    });

    // Add smooth curve
    this.intensityPath = 'M' + points.join(' L');
  }

  getX(time: number): number {
    return this.margin.left + (time / this.maxTime) * this.chartWidth;
  }

  getY(intensity: number): number {
    return this.margin.top + (1 - intensity / this.maxIntensity) * this.chartHeight;
  }

  getIntensityColor(intensity: number): string {
    if (intensity >= 8) return '#dc3545';
    if (intensity >= 6) return '#fd7e14';
    if (intensity >= 4) return '#ffc107';
    return '#28a745';
  }

  getStateColor(index: number): string {
    const colors = ['#007bff', '#6610f2', '#6f42c1', '#e83e8c', '#dc3545', '#fd7e14'];
    return colors[index % colors.length];
  }

  showBeatTooltip(beat: Beat, event: MouseEvent): void {
    const rect = (event.target as SVGElement).getBoundingClientRect();
    this.tooltip = {
      visible: true,
      x: rect.left + window.scrollX,
      y: rect.top + window.scrollY - 120,
      title: `Beat: ${beat.startTime.toFixed(1)}s - ${beat.endTime.toFixed(1)}s`,
      content: `
        <strong>Action:</strong> ${beat.action}<br>
        <strong>Consequence:</strong> ${beat.consequence}<br>
        <strong>Intensity:</strong> ${beat.intensity}/10<br>
        ${beat.isNewConsequence ? '<span style="color: #28a745;">✓ New Consequence</span>' : ''}
      `
    };
  }

  showConsequenceTooltip(marker: ConsequenceMarker, event: MouseEvent): void {
    const rect = (event.target as SVGElement).getBoundingClientRect();
    this.tooltip = {
      visible: true,
      x: rect.left + window.scrollX,
      y: rect.top + window.scrollY - 80,
      title: `New Consequence at ${marker.time.toFixed(1)}s`,
      content: `<strong>${marker.consequence}</strong>`
    };
  }

  onMouseMove(event: MouseEvent): void {
    // Update tooltip position if visible
    if (this.tooltip.visible) {
      const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
      this.tooltip.x = event.clientX - rect.left;
      this.tooltip.y = event.clientY - rect.top - 100;
    }
  }

  hideTooltip(): void {
    this.tooltip.visible = false;
  }
}
