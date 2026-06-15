#!/usr/bin/env python3
"""
Final Manuscript-Aligned AQF Runner

Orchestrates the complete AQF pipeline including evaluation, postprocessing,
reporting, and visualization for manuscript-aligned results.

Usage:
    python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed
    python aqf_manuscript_runner.py postprocess --results-dir results/aqf_eval
    python aqf_manuscript_runner.py report --results-dir results/aqf_eval
    python aqf_manuscript_runner.py visualize --results-dir results/aqf_eval
    python aqf_manuscript_runner.py all --data-dir dataset/mixed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from datetime import datetime


ROOT = Path(__file__).resolve().parent
EVALUATION_DIR = ROOT / "evaluation"


class AQFRunner:
    """Orchestrates the complete AQF manuscript pipeline."""
    
    # Manuscript-aligned default parameters
    DEFAULT_PARAMS = {
        "complexity_budget": 35,
        "theta": 0.10,
        "lambda_sc": 0.25,
        "mu": 0.25,
        "eta": 1.0,
        "random_trials": 30,
    }
    
    def __init__(self, verbose: bool = False, dry_run: bool = False):
        self.verbose = verbose
        self.dry_run = dry_run
        self.start_time = None
        self.pipeline_log = []
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] [{level}] {message}"
        print(log_msg)
        self.pipeline_log.append(log_msg)
    
    def run_command(
        self,
        cmd: list[str],
        description: str,
        check: bool = True
    ) -> Optional[subprocess.CompletedProcess]:
        """Execute a shell command with logging."""
        self.log(f"Running: {description}")
        if self.verbose:
            self.log(f"Command: {' '.join(cmd)}")
        
        if self.dry_run:
            self.log(f"[DRY RUN] Would execute: {' '.join(cmd)}", level="NOTICE")
            return None
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                check=check
            )
            if result.stdout:
                self.log(result.stdout.strip())
            if result.returncode == 0:
                self.log(f"✓ {description} completed successfully", level="SUCCESS")
            else:
                self.log(f"✗ {description} failed with return code {result.returncode}", level="ERROR")
                if result.stderr:
                    self.log(f"Error: {result.stderr}", level="ERROR")
            return result
        except subprocess.CalledProcessError as e:
            self.log(f"✗ Command failed: {e}", level="ERROR")
            if e.stderr:
                self.log(f"Error output: {e.stderr}", level="ERROR")
            raise
    
    def evaluate(
        self,
        data_dir: str,
        out_dir: str = "results/aqf_eval_manuscript",
        cache_dir: Optional[str] = None,
        use_cache: bool = True,
        complexity_budget: float = DEFAULT_PARAMS["complexity_budget"],
        theta: float = DEFAULT_PARAMS["theta"],
        lambda_sc: float = DEFAULT_PARAMS["lambda_sc"],
        mu: float = DEFAULT_PARAMS["mu"],
        eta: float = DEFAULT_PARAMS["eta"],
        random_trials: int = DEFAULT_PARAMS["random_trials"],
        seed: int = 42,
        **kwargs
    ) -> Path:
        """
        Run AQF evaluation on dataset.
        
        Args:
            data_dir: Path to dataset directory (e.g., dataset/mixed)
            out_dir: Output directory for results
            cache_dir: Cache directory for intermediate results
            use_cache: Whether to use cached data
            complexity_budget: Field complexity budget
            theta: Threshold parameter
            lambda_sc: Lambda score parameter
            mu: Mu parameter
            eta: Eta parameter
            random_trials: Number of random trials
            seed: Random seed
        
        Returns:
            Path to output directory
        """
        self.log(f"Starting AQF Evaluation")
        self.log(f"Data directory: {data_dir}")
        self.log(f"Output directory: {out_dir}")
        self.log(f"Parameters: complexity={complexity_budget}, theta={theta}, lambda_sc={lambda_sc}, mu={mu}, eta={eta}")
        
        cmd = [
            sys.executable,
            str(EVALUATION_DIR / "run_evaluation_final.py"),
            "--data-dir", data_dir,
            "--out-dir", out_dir,
            "--complexity-budget", str(complexity_budget),
            "--theta", str(theta),
            "--lambda-sc", str(lambda_sc),
            "--mu", str(mu),
            "--eta", str(eta),
            "--random-trials", str(random_trials),
            "--seed", str(seed),
        ]
        
        if cache_dir:
            cmd.extend(["--cache-dir", cache_dir])
        
        if use_cache:
            cmd.append("--use-cache")
        
        self.run_command(cmd, "AQF Evaluation")
        return Path(out_dir)
    
    def postprocess(
        self,
        results_dir: str,
        eta: float = DEFAULT_PARAMS["eta"],
        theta: float = DEFAULT_PARAMS["theta"],
        out_dir: Optional[str] = None,
        **kwargs
    ) -> Path:
        """
        Run postprocessing on evaluation results.
        
        Args:
            results_dir: Path to evaluation results directory
            eta: Eta parameter for postprocessing
            theta: Theta parameter
            out_dir: Output directory (defaults to results_dir)
        
        Returns:
            Path to results directory
        """
        if not out_dir:
            out_dir = results_dir
        
        self.log(f"Starting Postprocessing")
        self.log(f"Results directory: {results_dir}")
        self.log(f"Eta: {eta}, Theta: {theta}")
        
        cmd = [
            sys.executable,
            str(EVALUATION_DIR / "run_journal_postprocess.py"),
            "--results-dir", results_dir,
            "--eta", str(eta),
            "--theta", str(theta),
            "--out-dir", out_dir,
        ]
        
        self.run_command(cmd, "Postprocessing")
        return Path(out_dir)
    
    def report(
        self,
        results_dir: str,
        eta: float = DEFAULT_PARAMS["eta"],
        out_dir: Optional[str] = None,
        **kwargs
    ) -> Path:
        """
        Generate metrics report from results.
        
        Args:
            results_dir: Path to evaluation results directory
            eta: Eta parameter for metrics calculation
            out_dir: Output directory for reports
        
        Returns:
            Path to results directory
        """
        if not out_dir:
            out_dir = results_dir
        
        self.log(f"Starting Report Generation")
        self.log(f"Results directory: {results_dir}")
        
        cmd = [
            sys.executable,
            str(EVALUATION_DIR / "aqf_metrics_report.py"),
            "--results-dir", results_dir,
            "--eta", str(eta),
        ]
        
        if out_dir and out_dir != results_dir:
            cmd.extend(["--out-dir", out_dir])
        
        self.run_command(cmd, "Report Generation")
        return Path(out_dir)
    
    def visualize(
        self,
        results_dir: str,
        data_dir: Optional[str] = None,
        mu: float = DEFAULT_PARAMS["mu"],
        out_dir: Optional[str] = None,
        fig_width: int = 48,
        fig_height: int = 38,
        font_size: int = 15,
        max_field_labels: int = 200,
        **kwargs
    ) -> Path:
        """
        Generate schema graphs and visualizations.
        
        Args:
            results_dir: Path to evaluation results directory
            data_dir: Path to dataset directory (optional, for enhanced graphs)
            mu: Mu parameter for graph generation
            out_dir: Output directory for visualizations
            fig_width: Figure width
            fig_height: Figure height
            font_size: Font size for labels
            max_field_labels: Maximum number of field labels to show
        
        Returns:
            Path to visualization directory
        """
        if not out_dir:
            out_dir = Path(results_dir) / "schema_graphs"
        
        self.log(f"Starting Visualization Generation")
        self.log(f"Results directory: {results_dir}")
        self.log(f"Output directory: {out_dir}")
        
        cmd = [
            sys.executable,
            str(EVALUATION_DIR / "generate_aqf_schema_graphs.py"),
        ]
        
        if data_dir:
            cmd.extend(["--data-dir", data_dir])
        
        cmd.extend([
            "--results-dir", results_dir,
            "--out-dir", out_dir,
            "--mu", str(mu),
            "--fig-width", str(fig_width),
            "--fig-height", str(fig_height),
            "--font-size", str(font_size),
            "--max-field-labels", str(max_field_labels),
        ])
        
        self.run_command(cmd, "Visualization Generation")
        return Path(out_dir)
    
    def pipeline_all(
        self,
        data_dir: str,
        out_base: str = "results/aqf_manuscript",
        skip_evaluation: bool = False,
        skip_postprocess: bool = False,
        skip_report: bool = False,
        skip_visualization: bool = False,
        **kwargs
    ):
        """
        Execute the complete pipeline: evaluate → postprocess → report → visualize.
        
        Args:
            data_dir: Path to dataset directory
            out_base: Base output directory for all results
            skip_evaluation: Skip evaluation step
            skip_postprocess: Skip postprocessing step
            skip_report: Skip report generation
            skip_visualization: Skip visualization generation
            **kwargs: Additional parameters passed to individual steps
        """
        self.start_time = time.time()
        self.log("=" * 80)
        self.log("MANUSCRIPT-ALIGNED AQF PIPELINE STARTED")
        self.log("=" * 80)
        
        try:
            results_dir = Path(out_base)
            results_dir.mkdir(parents=True, exist_ok=True)
            
            # Step 1: Evaluate
            if not skip_evaluation:
                eval_dir = self.evaluate(
                    data_dir=data_dir,
                    out_dir=str(results_dir / "evaluation"),
                    **kwargs
                )
                results_dir = eval_dir.parent / eval_dir.name
            else:
                results_dir = results_dir / "evaluation"
                self.log("Skipping evaluation step")
            
            # Step 2: Postprocess
            if not skip_postprocess:
                self.postprocess(
                    results_dir=str(results_dir),
                    out_dir=str(results_dir),
                    **kwargs
                )
            else:
                self.log("Skipping postprocessing step")
            
            # Step 3: Report
            if not skip_report:
                self.report(
                    results_dir=str(results_dir),
                    out_dir=str(results_dir),
                    **kwargs
                )
            else:
                self.log("Skipping report generation step")
            
            # Step 4: Visualize
            if not skip_visualization:
                self.visualize(
                    results_dir=str(results_dir),
                    data_dir=data_dir,
                    out_dir=str(results_dir / "schema_graphs"),
                    **kwargs
                )
            else:
                self.log("Skipping visualization step")
            
            elapsed = time.time() - self.start_time
            self.log("=" * 80)
            self.log(f"PIPELINE COMPLETED SUCCESSFULLY in {elapsed:.1f}s")
            self.log("=" * 80)
            self.log(f"Results saved to: {results_dir}")
            
            # Save pipeline log
            log_path = results_dir / "pipeline.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.pipeline_log))
            self.log(f"Pipeline log saved to: {log_path}")
            
        except Exception as e:
            elapsed = time.time() - self.start_time if self.start_time else 0
            self.log(f"PIPELINE FAILED after {elapsed:.1f}s: {e}", level="ERROR")
            self.log("=" * 80)
            raise


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="Manuscript-aligned AQF runner for evaluation, postprocessing, reporting, and visualization",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run full evaluation
  python aqf_manuscript_runner.py evaluate --data-dir dataset/mixed

  # Run postprocessing on existing results
  python aqf_manuscript_runner.py postprocess --results-dir results/aqf_eval_manuscript/evaluation

  # Generate report
  python aqf_manuscript_runner.py report --results-dir results/aqf_eval_manuscript/evaluation

  # Generate visualizations
  python aqf_manuscript_runner.py visualize \\
    --results-dir results/aqf_eval_manuscript/evaluation \\
    --data-dir dataset/mixed

  # Run complete pipeline
  python aqf_manuscript_runner.py all --data-dir dataset/mixed

  # Dry run to see what would be executed
  python aqf_manuscript_runner.py all --data-dir dataset/mixed --dry-run
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose logging"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Evaluate command
    eval_parser = subparsers.add_parser("evaluate", help="Run AQF evaluation")
    eval_parser.add_argument(
        "--data-dir",
        required=True,
        help="Path to dataset directory (e.g., dataset/mixed)"
    )
    eval_parser.add_argument(
        "--out-dir",
        default="results/aqf_eval_manuscript/evaluation",
        help="Output directory for evaluation results"
    )
    eval_parser.add_argument(
        "--cache-dir",
        default=None,
        help="Cache directory for intermediate results"
    )
    eval_parser.add_argument(
        "--use-cache",
        action="store_true",
        default=True,
        help="Use cached data if available"
    )
    eval_parser.add_argument(
        "--complexity-budget",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["complexity_budget"],
        help="Field complexity budget (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--theta",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["theta"],
        help="Threshold parameter (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--lambda-sc",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["lambda_sc"],
        help="Lambda score parameter (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--mu",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["mu"],
        help="Mu parameter (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--eta",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["eta"],
        help="Eta parameter (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--random-trials",
        type=int,
        default=AQFRunner.DEFAULT_PARAMS["random_trials"],
        help="Number of random trials (default: %(default)s)"
    )
    eval_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)"
    )
    
    # Postprocess command
    post_parser = subparsers.add_parser("postprocess", help="Run postprocessing on results")
    post_parser.add_argument(
        "--results-dir",
        required=True,
        help="Path to evaluation results directory"
    )
    post_parser.add_argument(
        "--eta",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["eta"],
        help="Eta parameter (default: %(default)s)"
    )
    post_parser.add_argument(
        "--theta",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["theta"],
        help="Theta parameter (default: %(default)s)"
    )
    post_parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory (defaults to results-dir)"
    )
    
    # Report command
    report_parser = subparsers.add_parser("report", help="Generate metrics report")
    report_parser.add_argument(
        "--results-dir",
        required=True,
        help="Path to evaluation results directory"
    )
    report_parser.add_argument(
        "--eta",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["eta"],
        help="Eta parameter (default: %(default)s)"
    )
    report_parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for reports"
    )
    
    # Visualize command
    viz_parser = subparsers.add_parser("visualize", help="Generate visualizations")
    viz_parser.add_argument(
        "--results-dir",
        required=True,
        help="Path to evaluation results directory"
    )
    viz_parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to dataset directory (optional, for enhanced graphs)"
    )
    viz_parser.add_argument(
        "--mu",
        type=float,
        default=AQFRunner.DEFAULT_PARAMS["mu"],
        help="Mu parameter (default: %(default)s)"
    )
    viz_parser.add_argument(
        "--out-dir",
        default=None,
        help="Output directory for visualizations"
    )
    viz_parser.add_argument(
        "--fig-width",
        type=int,
        default=48,
        help="Figure width (default: 48)"
    )
    viz_parser.add_argument(
        "--fig-height",
        type=int,
        default=38,
        help="Figure height (default: 38)"
    )
    viz_parser.add_argument(
        "--font-size",
        type=int,
        default=15,
        help="Font size (default: 15)"
    )
    viz_parser.add_argument(
        "--max-field-labels",
        type=int,
        default=200,
        help="Maximum field labels (default: 200)"
    )
    
    # All command (full pipeline)
    all_parser = subparsers.add_parser(
        "all",
        help="Run complete pipeline: evaluate → postprocess → report → visualize"
    )
    all_parser.add_argument(
        "--data-dir",
        required=True,
        help="Path to dataset directory (e.g., dataset/mixed)"
    )
    all_parser.add_argument(
        "--out-base",
        default="results/aqf_manuscript",
        help="Base output directory for all results"
    )
    all_parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="Skip evaluation step"
    )
    all_parser.add_argument(
        "--skip-postprocess",
        action="store_true",
        help="Skip postprocessing step"
    )
    all_parser.add_argument(
        "--skip-report",
        action="store_true",
        help="Skip report generation"
    )
    all_parser.add_argument(
        "--skip-visualization",
        action="store_true",
        help="Skip visualization generation"
    )
    
    # Add parameters to all command
    for param_name, param_default in AQFRunner.DEFAULT_PARAMS.items():
        all_parser.add_argument(
            f"--{param_name.replace('_', '-')}",
            type=float if isinstance(param_default, float) else int,
            default=param_default,
            help=f"{param_name} parameter (default: {param_default})"
        )
    
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    runner = AQFRunner(verbose=args.verbose, dry_run=args.dry_run)
    
    try:
        if args.command == "evaluate":
            runner.evaluate(**vars(args))
        elif args.command == "postprocess":
            runner.postprocess(**vars(args))
        elif args.command == "report":
            runner.report(**vars(args))
        elif args.command == "visualize":
            runner.visualize(**vars(args))
        elif args.command == "all":
            runner.pipeline_all(**vars(args))
        else:
            parser.print_help()
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
