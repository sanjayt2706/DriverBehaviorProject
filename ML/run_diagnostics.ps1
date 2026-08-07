# ML/run_diagnostics.ps1
# PowerShell equivalent of run_diagnostics.sh for Windows 11

Write-Host "╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                    ML TRAINING SUMMARY - FULL DIAGNOSTIC                  ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

# Set location to ML folder
$ML_ROOT = Get-Location
Write-Host "Working directory: $ML_ROOT" -ForegroundColor Gray

# Verify we're in the ML folder
if (-not (Test-Path "src\ml_diagnostic.py")) {
    Write-Host "✗ Error: Not in ML folder. Please run from: DriverBehaviorProject\ML" -ForegroundColor Red
    exit 1
}

# Step 1: General diagnostic
Write-Host "`nStep 1: General Pipeline Diagnostic" -ForegroundColor Green
Write-Host "────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
python src/ml_diagnostic.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ ml_diagnostic.py failed" -ForegroundColor Red
    exit 1
}

# Step 2: Feature parity verification
Write-Host "`nStep 2: Feature Parity Verification" -ForegroundColor Green
Write-Host "────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
python src/verify_feature_parity.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ verify_feature_parity.py failed" -ForegroundColor Red
    exit 1
}

# Step 3: Class distribution analysis
Write-Host "`nStep 3: Class Distribution Analysis" -ForegroundColor Green
Write-Host "────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
python src/analyze_class_distribution.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ analyze_class_distribution.py failed" -ForegroundColor Red
    exit 1
}

# Step 4: Check SHAP completeness
Write-Host "`nStep 4: SHAP Feature Importance (checking for completeness)" -ForegroundColor Green
Write-Host "────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray

$shap_file = "outputs\shap_global_importance.json"
if (Test-Path $shap_file) {
    $shap_content = Get-Content $shap_file | ConvertFrom-Json
    $shap_count = $shap_content.importance.Count
    Write-Host "SHAP output found with $shap_count features" -ForegroundColor Yellow
    
    if ($shap_count -lt 24) {
        Write-Host "⚠ SHAP output incomplete ($shap_count/24 features), regenerating..." -ForegroundColor Yellow
        python src/step10_global_shap_fixed.py
    } else {
        Write-Host "✓ SHAP output complete ($shap_count features)" -ForegroundColor Green
    }
} else {
    Write-Host "✗ SHAP output not found, regenerating..." -ForegroundColor Yellow
    python src/step10_global_shap_fixed.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ SHAP generation failed" -ForegroundColor Red
    exit 1
}

# Step 5: Generate summary
Write-Host "`nStep 5: Generate Complete Training Summary" -ForegroundColor Green
Write-Host "────────────────────────────────────────────────────────────────────────────" -ForegroundColor Gray
python src/generate_training_summary.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ generate_training_summary.py failed" -ForegroundColor Red
    exit 1
}

# Final summary
Write-Host "`n╔════════════════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                           DIAGNOSTIC COMPLETE                             ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

Write-Host "`nOutput files generated:" -ForegroundColor Green
Write-Host "  • ML/ML_Training_Summary.md - Complete training summary" -ForegroundColor White
Write-Host "  • ML/outputs/class_distribution_analysis.json" -ForegroundColor White
Write-Host "  • ML/outputs/shap_global_importance.json (all 24 features)" -ForegroundColor White
Write-Host "  • ML/outputs/shap_global_importance.png (visualization)" -ForegroundColor White

Write-Host "`n✓ ML Training Summary is ready to review!" -ForegroundColor Green
Write-Host "`nNext step: Open and read ML/ML_Training_Summary.md" -ForegroundColor Yellow

# Try to open the summary in default text editor
if (Test-Path "ML_Training_Summary.md") {
    Write-Host "`nOpening summary file..." -ForegroundColor Gray
    Invoke-Item "ML_Training_Summary.md"
}
