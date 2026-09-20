#!/usr/bin/env python3
"""
Rockman Benchmark Results Reporter
Generates CSV and PNG reports with professional styling (black background, vibrant colors)
"""

import csv
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from matplotlib.patches import Rectangle
from matplotlib.table import Table


class RockmanResultsReporter:
    """Generates professional CSV and PNG reports for Rockman benchmark results."""
    
    # Color scheme - vibrant on black
    COLORS = {
        'bg': '#0a0a0a',           # Near black background
        'bg_alt': '#141414',       # Slightly lighter for alternating rows
        'header_bg': '#1a1a2e',    # Deep blue-black for headers
        'header_text': '#00d4ff',  # Bright cyan
        'text': '#e8e8e8',         # Near white text
        'text_dim': '#888888',     # Dim text for metadata
        'accent_cyan': '#00d4ff',  # Primary accent
        'accent_green': '#00ff88', # Success/passed
        'accent_red': '#ff3366',   # Failed
        'accent_orange': '#ffaa00', # Warning/partial
        'accent_purple': '#bb86fc', # Secondary accent
        'grid': '#2a2a3e',         # Subtle grid lines
        'border': '#00d4ff',       # Border color
    }
    
    # Difficulty labels
    DIFF_LABELS = {
        1: 'Introductory',
        2: 'Easy', 
        3: 'Intermediate',
        4: 'Advanced',
        5: 'Hard',
        6: 'Expert',
        7: 'Research'
    }
    
    def __init__(self, output_dir: str = "results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
    def generate_csv(self, leaderboard_data: Dict[str, Any], 
                     detailed_results: Dict[str, Any] = None,
                     filename: str = None) -> str:
        """Generate CSV report with all benchmark results."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rockman_results_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Metadata section
            writer.writerow(['# ROCKMAN BENCHMARK RESULTS'])
            writer.writerow(['# Generated:', datetime.now().isoformat()])
            writer.writerow(['# Benchmark Version:', leaderboard_data.get('benchmark_version', 'v0.2')])
            writer.writerow(['# Evaluator Version:', leaderboard_data.get('evaluator_version', '0.2.0')])
            writer.writerow(['# Protocol:', json.dumps(leaderboard_data.get('protocol', {}))])
            writer.writerow([])
            
            # Summary table
            writer.writerow(['MODEL SUMMARY'])
            writer.writerow([
                'Model', 'Provider', 'Version', 'Pass@1', 'Pass%', 
                'Solved', 'Total', 'Efficiency%', 'Robustness%', 
                'Temperature', 'Top-p', 'Max Tokens', 'k', 'Hardware', 'Date'
            ])
            
            for model_name, model_data in leaderboard_data.get('models', {}).items():
                score = model_data.get('score', {})
                overall = model_data.get('overall', 0)
                passed = score.get('passed_tasks', 0)
                total = score.get('total_tasks', 0)
                eff = score.get('efficiency_score', 0)
                rob = score.get('robustness_score', 0)
                protocol = leaderboard_data.get('protocol', {})
                
                writer.writerow([
                    model_name,
                    model_data.get('provider', ''),
                    model_data.get('model_version', ''),
                    f"{overall:.4f}",
                    f"{overall*100:.2f}%",
                    passed,
                    total,
                    f"{eff:.2f}%",
                    f"{rob:.2f}%",
                    protocol.get('temperature', ''),
                    protocol.get('top_p', ''),
                    protocol.get('max_tokens', ''),
                    protocol.get('k', ''),
                    protocol.get('hardware', ''),
                    model_data.get('date', '')
                ])
            
            writer.writerow([])
            
            # Difficulty breakdown
            writer.writerow(['BY DIFFICULTY'])
            writer.writerow(['Model'] + [f'Level {d} ({self.DIFF_LABELS.get(d, "")})' for d in range(1, 8)])
            
            for model_name, model_data in leaderboard_data.get('models', {}).items():
                score = model_data.get('score', {})
                row = [model_name]
                for d in range(1, 8):
                    val = score.get('by_difficulty', {}).get(d, 0)
                    row.append(f"{val:.2f}%")
                writer.writerow(row)
            
            writer.writerow([])
            
            # Category breakdown
            writer.writerow(['BY CATEGORY'])
            all_categories = set()
            for model_data in leaderboard_data.get('models', {}).values():
                all_categories.update(model_data.get('score', {}).get('by_category', {}).keys())
            all_categories = sorted(all_categories)
            
            writer.writerow(['Model'] + all_categories)
            for model_name, model_data in leaderboard_data.get('models', {}).items():
                score = model_data.get('score', {})
                row = [model_name]
                for cat in all_categories:
                    val = score.get('by_category', {}).get(cat, 0)
                    row.append(f"{val:.2f}%")
                writer.writerow(row)
            
            writer.writerow([])
            
            # Task Type breakdown
            writer.writerow(['BY TASK TYPE'])
            all_task_types = set()
            for model_data in leaderboard_data.get('models', {}).values():
                all_task_types.update(model_data.get('score', {}).get('by_task_type', {}).keys())
            all_task_types = sorted(all_task_types)
            
            writer.writerow(['Model'] + all_task_types)
            for model_name, model_data in leaderboard_data.get('models', {}).items():
                score = model_data.get('score', {})
                row = [model_name]
                for tt in all_task_types:
                    val = score.get('by_task_type', {}).get(tt, 0)
                    row.append(f"{val:.2f}%")
                writer.writerow(row)
            
            # Language breakdown
            writer.writerow([])
            writer.writerow(['BY LANGUAGE'])
            all_languages = set()
            for model_data in leaderboard_data.get('models', {}).values():
                all_languages.update(model_data.get('score', {}).get('by_language', {}).keys())
            all_languages = sorted(all_languages)
            
            writer.writerow(['Model'] + all_languages)
            for model_name, model_data in leaderboard_data.get('models', {}).items():
                score = model_data.get('score', {})
                row = [model_name]
                for lang in all_languages:
                    val = score.get('by_language', {}).get(lang, 0)
                    row.append(f"{val:.2f}%")
                writer.writerow(row)
            
            # Detailed per-problem results if available
            if detailed_results:
                writer.writerow([])
                writer.writerow(['DETAILED PER-PROBLEM RESULTS'])
                writer.writerow(['Model', 'Task ID', 'Category', 'Subcategory', 'Difficulty', 
                                'Task Type', 'Language', 'Passed', 'Pass@k', 
                                'Runtime (ms)', 'Memory (MB)', 'Error Type'])
                
                for model_name, model_results in detailed_results.items():
                    if isinstance(model_results, list):
                        # Handle list format (API_ERROR cases)
                        for task_id, runs in enumerate(model_results):
                            if isinstance(runs, list):
                                for run in runs:
                                    for er in run.get('results', []):
                                        writer.writerow([
                                            model_name,
                                            task_id,
                                            '',  # category - would need problem lookup
                                            '',  # subcategory
                                            '',  # difficulty
                                            '',  # task_type
                                            '',  # language
                                            'PASS' if run.get('passed') else 'FAIL',
                                            f"{run.get('pass_at_k', 0):.4f}",
                                            f"{er.get('execution_time_ms', 0):.1f}",
                                            f"{er.get('memory_used_mb', 0):.1f}",
                                            er.get('error_type', '') or ''
                                        ])
                    elif isinstance(model_results, dict):
                        # Handle dict format
                        for task_id, runs in model_results.items():
                            for run in runs:
                                for er in run.get('results', []):
                                    writer.writerow([
                                        model_name,
                                        task_id,
                                        '',  # category - would need problem lookup
                                        '',  # subcategory
                                        '',  # difficulty
                                        '',  # task_type
                                        '',  # language
                                        'PASS' if run.get('passed') else 'FAIL',
                                        f"{run.get('pass_at_k', 0):.4f}",
                                        f"{er.get('execution_time_ms', 0):.1f}",
                                        f"{er.get('memory_used_mb', 0):.1f}",
                                        er.get('error_type', '') or ''
                                    ])
        
        print(f"✅ CSV report saved: {filepath}")
        return str(filepath)
    
    def generate_png(self, leaderboard_data: Dict[str, Any],
                     filename: str = None,
                     width: int = 1920,
                     height: int = 1080,
                     dpi: int = 150) -> str:
        """Generate professional PNG report with black background and vibrant colors."""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"rockman_results_{timestamp}.png"
        
        filepath = self.output_dir / filename
        
        # Setup figure with black background
        fig = plt.figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        fig.patch.set_facecolor(self.COLORS['bg'])
        
        # Create grid layout
        gs = fig.add_gridspec(4, 3, height_ratios=[0.8, 2.5, 2.5, 1.2], 
                              hspace=0.35, wspace=0.25, 
                              left=0.05, right=0.95, top=0.93, bottom=0.05)
        
        # Title bar
        ax_title = fig.add_subplot(gs[0, :])
        self._draw_title_bar(ax_title, leaderboard_data)
        
        # Main leaderboard table
        ax_main = fig.add_subplot(gs[1, :])
        self._draw_leaderboard_table(ax_main, leaderboard_data)
        
        # Difficulty breakdown (left)
        ax_diff = fig.add_subplot(gs[2, 0])
        self._draw_difficulty_chart(ax_diff, leaderboard_data)
        
        # Category breakdown (center)
        ax_cat = fig.add_subplot(gs[2, 1])
        self._draw_category_chart(ax_cat, leaderboard_data)
        
        # Task Type / Language breakdown (right)
        ax_tt = fig.add_subplot(gs[2, 2])
        self._draw_task_type_chart(ax_tt, leaderboard_data)
        
        # Footer with metadata
        ax_footer = fig.add_subplot(gs[3, :])
        self._draw_footer(ax_footer, leaderboard_data)
        
        plt.savefig(filepath, facecolor=self.COLORS['bg'], dpi=dpi, 
                    bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        
        print(f"✅ PNG report saved: {filepath}")
        return str(filepath)
    
    def _draw_title_bar(self, ax, data):
        """Draw title bar with benchmark info."""
        ax.set_facecolor(self.COLORS['header_bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Main title
        ax.text(0.02, 0.65, 'ROCKMAN BENCHMARK', 
                fontsize=28, fontweight='bold', color=self.COLORS['accent_cyan'],
                fontfamily='monospace')
        ax.text(0.02, 0.3, 'v0.2 Official Evaluation', 
                fontsize=16, color=self.COLORS['accent_purple'],
                fontfamily='monospace')
        
        # Metadata on right
        protocol = data.get('protocol', {})
        eval_date = data.get('evaluation_date', '')[:10]
        meta_text = (
            f"Date: {eval_date}\n"
            f"Tasks: {data.get('models', {}).get(list(data.get('models', {}).keys())[0], {}).get('score', {}).get('total_tasks', 44)}\n"
            f"k={data.get('protocol', {}).get('k', 1)} | "
            f"Temp={data.get('protocol', {}).get('temperature', 0)} | "
            f"Tokens={data.get('protocol', {}).get('max_tokens', 4096)}"
        )
        ax.text(0.98, 0.5, meta_text, 
                fontsize=11, color=self.COLORS['text_dim'],
                ha='right', va='center', fontfamily='monospace')
        
        # Decorative line
        ax.axhline(y=0.1, color=self.COLORS['accent_cyan'], linewidth=2, alpha=0.5)
    
    def _draw_leaderboard_table(self, ax, data):
        """Draw main leaderboard table."""
        ax.set_facecolor(self.COLORS['bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        models = data.get('models', {})
        if not models:
            return
        
        # Prepare data
        headers = ['Rank', 'Model', 'Provider', 'Pass@1', 'Efficiency', 'Robustness', 'Solved/Total']
        rows = []
        
        sorted_models = sorted(models.items(), key=lambda x: x[1].get('overall', 0), reverse=True)
        
        for rank, (name, mdata) in enumerate(sorted_models, 1):
            score = mdata.get('score', {})
            overall = mdata.get('overall', 0)
            eff = score.get('efficiency_score', 0)
            rob = score.get('robustness_score', 0)
            passed = score.get('passed_tasks', 0)
            total = score.get('total_tasks', 0)
            provider = mdata.get('provider', '')
            
            rows.append([
                f"#{rank}",
                name[:25] + '...' if len(name) > 25 else name,
                provider[:15],
                f"{overall*100:.1f}%",
                f"{eff:.1f}%",
                f"{rob:.1f}%",
                f"{passed}/{total}"
            ])
        
        # Draw table
        table = self._create_styled_table(ax, headers, rows, 
                                          col_widths=[0.06, 0.25, 0.15, 0.12, 0.12, 0.12, 0.16],
                                          start_y=0.92, row_height=0.07)
    
    def _create_styled_table(self, ax, headers, rows, col_widths, start_y, row_height):
        """Create a styled table with alternating row colors."""
        x_start = 0.02
        y = start_y
        
        # Header
        x = x_start
        for i, (header, width) in enumerate(zip(headers, col_widths)):
            rect = Rectangle((x, y), width, row_height, 
                           facecolor=self.COLORS['header_bg'], 
                           edgecolor=self.COLORS['border'], linewidth=1)
            ax.add_patch(rect)
            ax.text(x + width/2, y + row_height/2, header,
                   ha='center', va='center', fontsize=10, fontweight='bold',
                   color=self.COLORS['header_text'], fontfamily='monospace')
            x += width
        
        y -= row_height
        
        # Rows
        for row_idx, row in enumerate(rows):
            x = x_start
            bg_color = self.COLORS['bg_alt'] if row_idx % 2 == 0 else self.COLORS['bg']
            
            for i, (cell, width) in enumerate(zip(row, col_widths)):
                rect = Rectangle((x, y), width, row_height,
                               facecolor=bg_color,
                               edgecolor=self.COLORS['grid'], linewidth=0.5)
                ax.add_patch(rect)
                
                # Color coding for Pass@1 column
                cell_color = self.COLORS['text']
                if i == 3:  # Pass@1 column
                    try:
                        val = float(cell.replace('%', ''))
                        if val >= 50:
                            cell_color = self.COLORS['accent_green']
                        elif val >= 20:
                            cell_color = self.COLORS['accent_orange']
                        elif val > 0:
                            cell_color = self.COLORS['accent_purple']
                        else:
                            cell_color = self.COLORS['accent_red']
                    except:
                        pass
                
                ax.text(x + 0.005, y + row_height/2, cell,
                       ha='left' if i > 0 else 'center', va='center', 
                       fontsize=9, color=cell_color, fontfamily='monospace')
                x += width
            y -= row_height
        
        return y
    
    def _draw_difficulty_chart(self, ax, data):
        """Draw difficulty breakdown horizontal bar chart."""
        ax.set_facecolor(self.COLORS['bg'])
        ax.set_title('BY DIFFICULTY', fontsize=12, fontweight='bold', 
                    color=self.COLORS['accent_cyan'], pad=10, fontfamily='monospace')
        
        models = data.get('models', {})
        if not models:
            return
        
        # Get difficulties present
        all_diffs = set()
        for mdata in models.values():
            all_diffs.update(mdata.get('score', {}).get('by_difficulty', {}).keys())
        # Handle both int and string keys
        diffs = sorted(all_diffs, key=lambda x: int(x) if isinstance(x, (int, str)) and str(x).isdigit() else 0)
        
        if not diffs:
            return
        
        model_names = list(models.keys())[:6]  # Limit to 6 models
        n_models = len(model_names)
        bar_height = 0.12
        y_positions = np.arange(len(diffs))
        
        colors = [self.COLORS['accent_cyan'], self.COLORS['accent_green'], 
                  self.COLORS['accent_orange'], self.COLORS['accent_purple'],
                  self.COLORS['accent_red'], '#00ffff']
        
        for i, model_name in enumerate(model_names):
            score = models[model_name].get('score', {})
            diffs_data = score.get('by_difficulty', {})
            
            values = [diffs_data.get(d, 0) for d in diffs]
            y_offset = (i - n_models/2 + 0.5) * (bar_height / n_models)
            
            bars = ax.barh(y_positions + y_offset, values, bar_height/n_models,
                          color=colors[i % len(colors)], alpha=0.85,
                          edgecolor='white', linewidth=0.5,
                          label=model_name[:15])
            
            # Add value labels
            for bar, val in zip(bars, values):
                if val > 0:
                    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                           f'{val:.0f}%', va='center', ha='left',
                           fontsize=7, color=self.COLORS['text'], fontweight='bold')
        
        ax.set_yticks(y_positions)
        ax.set_yticklabels([f'L{d} {self.DIFF_LABELS.get(d, "")[:12]}' for d in diffs],
                          fontsize=8, color=self.COLORS['text'])
        ax.set_xlim(0, 105)
        ax.set_xlabel('Pass Rate %', color=self.COLORS['text_dim'], fontsize=8)
        ax.tick_params(colors=self.COLORS['text_dim'], labelsize=7)
        ax.legend(loc='lower right', fontsize=6, framealpha=0.8,
                 facecolor=self.COLORS['bg_alt'], edgecolor=self.COLORS['grid'])
        ax.set_facecolor(self.COLORS['bg'])
        for spine in ax.spines.values():
            spine.set_color(self.COLORS['grid'])
    
    def _draw_category_chart(self, ax, data):
        """Draw category breakdown chart."""
        ax.set_facecolor(self.COLORS['bg'])
        ax.set_title('BY CATEGORY', fontsize=12, fontweight='bold',
                    color=self.COLORS['accent_green'], pad=10, fontfamily='monospace')
        
        models = data.get('models', {})
        if not models:
            return
        
        # Get top categories
        all_cats = set()
        for mdata in models.values():
            all_cats.update(mdata.get('score', {}).get('by_category', {}).keys())
        
        # Sort by average performance
        cat_scores = {}
        for cat in all_cats:
            scores = [m.get('score', {}).get('by_category', {}).get(cat, 0) 
                     for m in models.values()]
            cat_scores[cat] = np.mean(scores)
        
        top_cats = sorted(cat_scores.keys(), key=lambda x: -cat_scores[x])[:6]
        
        if not top_cats:
            return
        
        model_names = list(models.keys())[:5]
        n_models = len(model_names)
        
        colors = [self.COLORS['accent_green'], self.COLORS['accent_cyan'],
                  self.COLORS['accent_orange'], self.COLORS['accent_purple'],
                  self.COLORS['accent_red']]
        
        x = np.arange(len(top_cats))
        width = 0.15
        
        for i, model_name in enumerate(model_names):
            score = models[model_name].get('score', {})
            cats_data = score.get('by_category', {})
            values = [cats_data.get(cat, 0) for cat in top_cats]
            
            offset = (i - n_models/2 + 0.5) * width
            bars = ax.bar(x + offset, values, width, 
                         color=colors[i % len(colors)], alpha=0.85,
                         label=model_name[:12], edgecolor='white', linewidth=0.3)
        
        ax.set_xticks(x)
        ax.set_xticklabels([c[:10] for c in top_cats], rotation=15, ha='right',
                          fontsize=7, color=self.COLORS['text'])
        ax.set_ylabel('Pass Rate %', color=self.COLORS['text_dim'], fontsize=8)
        ax.set_ylim(0, 105)
        ax.tick_params(colors=self.COLORS['text_dim'], labelsize=7)
        ax.legend(loc='upper right', fontsize=6, framealpha=0.8,
                 facecolor=self.COLORS['bg_alt'], edgecolor=self.COLORS['grid'],
                 ncol=2)
        ax.set_facecolor(self.COLORS['bg'])
        for spine in ax.spines.values():
            spine.set_color(self.COLORS['grid'])
    
    def _draw_task_type_chart(self, ax, data):
        """Draw task type + language chart."""
        ax.set_facecolor(self.COLORS['bg'])
        ax.set_title('TASK TYPE / LANGUAGE', fontsize=12, fontweight='bold',
                    color=self.COLORS['accent_orange'], pad=10, fontfamily='monospace')
        
        models = data.get('models', {})
        if not models:
            return
        
        # Task types pie (first model)
        first_model = list(models.values())[0]
        score = first_model.get('score', {})
        tt_data = score.get('by_task_type', {})
        lang_data = score.get('by_language', {})
        
        # Filter out zero values
        tt_data = {k: v for k, v in tt_data.items() if v > 0}
        lang_data = {k: v for k, v in lang_data.items() if v > 0}
        
        if tt_data:
            # Task type donut chart
            labels = list(tt_data.keys())
            values = list(tt_data.values())
            colors = [self.COLORS['accent_cyan'], self.COLORS['accent_green'],
                     self.COLORS['accent_orange'], self.COLORS['accent_purple'],
                     self.COLORS['accent_red'], self.COLORS['accent_purple']]
            
            wedges, texts, autotexts = ax.pie(values, labels=labels, 
                                             colors=colors[:len(values)],
                                             autopct='%1.0f%%', startangle=90,
                                             pctdistance=0.75, labeldistance=1.1,
                                             wedgeprops=dict(width=0.5, edgecolor=self.COLORS['bg'],
                                                           linewidth=2))
            
            for text in texts:
                text.set_color(self.COLORS['text'])
                text.set_fontsize(7)
            for autotext in autotexts:
                autotext.set_color(self.COLORS['bg'])
                autotext.set_fontsize(8)
                autotext.set_fontweight('bold')
            
            ax.set_title(f'Task Types ({list(models.keys())[0][:15]})', 
                        fontsize=9, color=self.COLORS['text_dim'], pad=5)
        elif lang_data:
            # Language bar chart if no task types
            labels = list(lang_data.keys())
            values = list(lang_data.values())
            colors = [self.COLORS['accent_cyan'], self.COLORS['accent_green'],
                     self.COLORS['accent_orange'], self.COLORS['accent_purple'],
                     self.COLORS['accent_red']]
            
            y_pos = np.arange(len(labels))
            bars = ax.barh(y_pos, values, color=colors[:len(values)], alpha=0.85,
                          edgecolor='white', linewidth=0.5)
            ax.set_yticks(y_pos)
            ax.set_yticklabels(labels, fontsize=8, color=self.COLORS['text'])
            ax.set_xlim(0, max(values) * 1.2)
            ax.set_xlabel('Pass Rate %', color=self.COLORS['text_dim'], fontsize=8)
            ax.tick_params(colors=self.COLORS['text_dim'], labelsize=7)
            for bar, val in zip(bars, values):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2,
                       f'{val:.0f}%', va='center', ha='left',
                       fontsize=7, color=self.COLORS['text'], fontweight='bold')
            ax.set_title(f'Languages ({list(models.keys())[0][:15]})', 
                        fontsize=9, color=self.COLORS['text_dim'], pad=5)
        else:
            ax.text(0.5, 0.5, 'No task type/language data', 
                   ha='center', va='center', fontsize=9, color=self.COLORS['text_dim'])
        
        ax.set_facecolor(self.COLORS['bg'])
        for spine in ax.spines.values():
            spine.set_visible(False)
    
    def _draw_footer(self, ax, data):
        """Draw footer with metadata."""
        ax.set_facecolor(self.COLORS['header_bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        protocol = data.get('protocol', {})
        evaluator = data.get('evaluator_version', '0.2.0')
        bench_ver = data.get('benchmark_version', 'v0.2')
        
        footer_text = (
            f"Rockman Benchmark v{bench_ver} | Evaluator v{evaluator} | "
            f"Protocol: Pass@{protocol.get('k', 1)} | Temp: {protocol.get('temperature', 0)} | "
            f"Top-p: {protocol.get('top_p', 1)} | Max Tokens: {protocol.get('max_tokens', 4096)} | "
            f"Hardware: {protocol.get('hardware', 'N/A')} | "
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        ax.text(0.5, 0.5, footer_text, ha='center', va='center',
               fontsize=9, color=self.COLORS['text_dim'], fontfamily='monospace')
        
        # Decorative line
        ax.axhline(y=0.85, color=self.COLORS['accent_cyan'], linewidth=1, alpha=0.3)
    
    def generate_full_report(self, leaderboard_data: Dict[str, Any],
                             detailed_results: Dict[str, Any] = None,
                             prefix: str = "rockman") -> Dict[str, str]:
        """Generate both CSV and PNG reports."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"{prefix}_results_{timestamp}.csv"
        png_file = f"{prefix}_results_{timestamp}.png"
        
        csv_path = self.generate_csv(leaderboard_data, detailed_results, csv_file)
        png_path = self.generate_png(leaderboard_data, png_file)
        
        return {'csv': csv_path, 'png': png_path}


def auto_generate_reports(leaderboard_file: str = "rockman_v0.2_leaderboard.json",
                          output_dir: str = "results") -> Dict[str, str]:
    """Auto-generate CSV and PNG reports from leaderboard file."""
    with open(leaderboard_file, 'r') as f:
        leaderboard = json.load(f)
    
    reporter = RockmanResultsReporter(output_dir)
    return reporter.generate_full_report(leaderboard)


if __name__ == "__main__":
    # Demo with sample data
    sample_data = {
        "benchmark_version": "v0.2",
        "evaluator_version": "0.2.0",
        "evaluation_date": "2024-09-20T10:30:00Z",
        "protocol": {
            "k": 1, "temperature": 0.0, "top_p": 1.0, 
            "max_tokens": 4096, "hardware": "H100"
        },
        "models": {
            "gpt-4o": {
                "model_version": "2024-08",
                "provider": "openai",
                "overall": 0.724,
                "score": {
                    "overall": 72.4,
                    "passed_tasks": 319, "total_tasks": 440,
                    "efficiency_score": 68.2,
                    "robustness_score": 71.5,
                    "by_difficulty": {1: 98.5, 2: 94.2, 3: 82.1, 4: 68.3, 5: 51.7, 6: 32.4, 7: 14.8},
                    "by_category": {
                        "Fundamentals": 89.3, "Data Structures": 81.2, 
                        "Algorithms": 76.8, "Graphs": 74.1, "Trees": 69.5,
                        "Math": 65.2, "Debugging": 55.8, "Optimization": 44.3,
                        "Stateful Systems": 51.2, "Multi-step": 47.9
                    },
                    "by_task_type": {"generation": 78.4, "debugging": 55.8, 
                                    "optimization": 44.3, "stateful": 51.2, "multi_step": 47.9},
                    "by_language": {"python": 72.4, "cpp": 68.1, "rust": 65.8},
                    "passed_tasks": 319, "total_tasks": 440
                }
            },
            "template": {
                "model_version": "1.0", "provider": "rockman",
                "overall": 0.136,
                "score": {
                    "overall": 13.6, "passed_tasks": 6, "total_tasks": 44,
                    "efficiency_score": 0.0, "robustness_score": 15.2,
                    "by_difficulty": {3: 27.3, 4: 0.0, 5: 0.0},
                    "by_category": {"Debugging": 42.9},
                    "by_task_type": {"debugging": 42.9, "generation": 0.0},
                    "by_language": {"python": 13.6},
                    "passed_tasks": 6, "total_tasks": 44
                }
            }
        }
    }
    
    reporter = RockmanResultsReporter("results")
    result = reporter.generate_full_report(sample_data, prefix="rockman_v0.2")
    print(f"\nGenerated: {result['csv']} and {result['png']}")