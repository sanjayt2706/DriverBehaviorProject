#!/usr/bin/env python3
"""
ML/run_diagnostics_windows.py
Pure Python version of diagnostics for Windows (no PowerShell needed)
Run from ML folder: python run_diagnostics_windows.py

Uses ONLY files that exist in ML.zip:
  - src/verify_feature_parity.py
  - src/analyze_class_distribution.py
  - src/step10_global_shap_fixed.py
  - src/generate_training_summary.py
"""
import subprocess
import sys
import json
import os
from pathlib import Path

# ANSI color codes (Windows 10+ supports them in terminal)
class Color:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Color.OKCYAN}{'='*80}{Color.ENDC}")
    print(f"{Color.OKCYAN}{text:^80}{Color.ENDC}")
    print(f"{Color.OKCYAN}{'='*80}{Color.ENDC}\n")

def print_step(step_num, text):
    print(f"\n{Color.OKGREEN}Step {step_num}: {text}{Color.ENDC}")
    print(f"{Color.OKGREEN}{'-'*80}{Color.ENDC}")

def run_script(script_name, description):
    """Run a Python script and return True if successful"""
    print(f"{Color.OKBLUE}Running: {script_name}{Color.ENDC}")
    
    script_path = Path("src") / script_name
    if not script_path.exists():
        print(f"{Color.FAIL}✗ {script_path} not found{Color.ENDC}")
        return False
    
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=Path.cwd(),
            capture_output=False
        )
        if result.returncode == 0:
            print(f"{Color.OKGREEN}✓ {description} completed{Color.ENDC}")
            return True
        else:
            print(f"{Color.FAIL}✗ {description} failed with exit code {result.returncode}{Color.ENDC}")
            return False
    except Exception as e:
        print(f"{Color.FAIL}✗ Error running {script_name}: {e}{Color.ENDC}")
        return False

def check_shap_completeness():
    """Check if SHAP output has all 24 features"""
    shap_file = Path("outputs") / "shap_global_importance.json"
    
    if not shap_file.exists():
        print(f"{Color.WARNING}✗ SHAP output not found, regenerating...{Color.ENDC}")
        return run_script("step10_global_shap_fixed.py", "SHAP generation")
    
    try:
        with open(shap_file) as f:
            data = json.load(f)
        shap_count = len(data.get("importance", []))
        
        if shap_count < 24:
            print(f"{Color.WARNING}⚠ SHAP output incomplete ({shap_count}/24 features), regenerating...{Color.ENDC}")
            return run_script("step10_global_shap_fixed.py", "SHAP regeneration")
        else:
            print(f"{Color.OKGREEN}✓ SHAP output complete ({shap_count} features){Color.ENDC}")
            return True
    except Exception as e:
        print(f"{Color.FAIL}✗ Error checking SHAP: {e}{Color.ENDC}")
        return False

def main():
    print_header("ML TRAINING SUMMARY - FULL DIAGNOSTIC")
    
    ml_root = Path.cwd()
    print(f"Working directory: {ml_root}")
    
    # Verify we're in ML folder
    if not (Path("src") / "verify_feature_parity.py").exists():
        print(f"{Color.FAIL}✗ Error: Not in ML folder.{Color.ENDC}")
        print(f"{Color.FAIL}Please run from: DriverBehaviorProject/ML{Color.ENDC}")
        sys.exit(1)
    
    # Step 1: Feature parity verification
    print_step(1, "Feature Parity Verification")
    print(f"{Color.OKBLUE}Verifies curve_density, all 24 features, and feature parity{Color.ENDC}")
    if not run_script("verify_feature_parity.py", "Feature parity"):
        sys.exit(1)
    
    # Step 2: Class distribution analysis
    print_step(2, "Class Distribution Analysis")
    print(f"{Color.OKBLUE}Reports LOW/MEDIUM/HIGH counts and balancing recommendations{Color.ENDC}")
    if not run_script("analyze_class_distribution.py", "Class distribution analysis"):
        sys.exit(1)
    
    # Step 3: Check and regenerate SHAP if needed
    print_step(3, "SHAP Feature Importance (checking for completeness)")
    print(f"{Color.OKBLUE}Verifies all 24 features are ranked by importance{Color.ENDC}")
    if not check_shap_completeness():
        sys.exit(1)
    
    # Step 4: Generate summary
    print_step(4, "Generate Complete Training Summary")
    print(f"{Color.OKBLUE}Compiles all results into ML_Training_Summary.md{Color.ENDC}")
    if not run_script("generate_training_summary.py", "Training summary generation"):
        sys.exit(1)
    
    # Final summary
    print_header("DIAGNOSTIC COMPLETE")
    
    print(f"{Color.OKGREEN}Output files generated:{Color.ENDC}")
    print(f"  • ML/ML_Training_Summary.md - Complete training summary")
    print(f"  • ML/outputs/class_distribution_analysis.json")
    print(f"  • ML/outputs/shap_global_importance.json (all 24 features)")
    print(f"  • ML/outputs/shap_global_importance.png (visualization)")
    
    print(f"\n{Color.OKGREEN}✓ ML Training Summary is ready to review!{Color.ENDC}")
    print(f"{Color.WARNING}Next step: Open and read ML/ML_Training_Summary.md{Color.ENDC}")
    
    # Try to open the summary file
    summary_file = Path("ML_Training_Summary.md")
    if summary_file.exists():
        print(f"\n{Color.OKBLUE}Summary file location: {summary_file.absolute()}{Color.ENDC}")
        print(f"{Color.OKGREEN}You can now open ML_Training_Summary.md in your text editor{Color.ENDC}")

if __name__ == "__main__":
    main()