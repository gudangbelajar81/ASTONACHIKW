# Script to fix remaining hard-coded URLs in frontend

$files = @(
    "frontend/app/explain/page.tsx",
    "frontend/app/ohlcv/page.tsx",
    "frontend/app/opportunities/page.tsx",
    "frontend/app/performance/page.tsx",
    "frontend/app/portfolio/page.tsx",
    "frontend/app/report/page.tsx",
    "frontend/app/settings/page.tsx"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "Processing $file..."
        $content = Get-Content $file -Raw
        
        # Pattern for hard-coded URL definition
        $pattern = 'const API_BASE_URL =\s+process\.env\.NEXT_PUBLIC_BACKEND_URL \?\? process\.env\.NEXT_PUBLIC_API_URL \?\? "https://astonachikw-production\.up\.railway\.app";'
        
        if ($content -match $pattern) {
            # Add import if not present
            if ($content -notmatch 'import \{ getApiBaseUrl \}') {
                $content = $content -replace '(import .+ from [''"]\.\.\/\.\.\/lib\/userData[''"];)', "`$1`nimport { getApiBaseUrl } from `"../../lib/apiBase`";"
            }
            
            # Replace the URL definition
            $content = $content -replace $pattern, 'const API_BASE_URL = getApiBaseUrl();'
            
            Set-Content $file -Value $content -NoNewline
            Write-Host "  ✅ Updated $file"
        } else {
            Write-Host "  ℹ Pattern not found in $file"
        }
    } else {
        Write-Host "  ❌ File not found: $file"
    }
}

Write-Host "`nDone fixing remaining hard-coded URLs!"