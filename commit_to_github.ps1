# PowerShell script to clean up and commit to GitHub
# Run this script from the AquaMind project root directory

# Step 1: Run the cleanup script to remove cache files
Write-Host "Running cleanup script..." -ForegroundColor Green
python cleanup_for_git.py --force

# Step 2: Check git status
Write-Host "`nCurrent git status:" -ForegroundColor Green
git status

# Step 3: Prompt for commit message
$commitMessage = Read-Host "`nEnter commit message"
if ([string]::IsNullOrWhiteSpace($commitMessage)) {
    $commitMessage = "Update implementation plan and clean up repository"
}

# Step 4: Add all changes
Write-Host "`nAdding all changes to git..." -ForegroundColor Green
git add .

# Step 5: Commit changes
Write-Host "`nCommitting changes with message: $commitMessage" -ForegroundColor Green
git commit -m "$commitMessage"

# Step 6: Push to GitHub
$confirmPush = Read-Host "`nPush changes to GitHub? (y/n)"
if ($confirmPush -eq "y") {
    Write-Host "`nPushing changes to GitHub..." -ForegroundColor Green
    git push
    Write-Host "`nChanges successfully pushed to GitHub!" -ForegroundColor Green
} else {
    Write-Host "`nSkipping push to GitHub. You can push manually later with 'git push'" -ForegroundColor Yellow
}
