# deploy.ps1 - 다운로드된 최신 main.py를 프로젝트에 반영하고 배포까지 자동 실행
# (배포 성공 후, Downloads 폴더의 낡은 main*.py 사본들도 자동으로 정리합니다)

$commitMsg = if ($args[0]) { $args[0] } else { "업데이트 " + (Get-Date -Format "yyyy-MM-dd HH:mm") }

# 1. Downloads 폴더에서 가장 최근에 받은 main.py 찾기
$downloadedFiles = Get-ChildItem "$env:USERPROFILE\Downloads\main*.py" |
    Sort-Object LastWriteTime -Descending

$latest = $downloadedFiles | Select-Object -First 1

if (-not $latest) {
    Write-Host "❌ Downloads 폴더에서 main.py를 찾지 못했습니다. 먼저 다운로드해주세요." -ForegroundColor Red
    exit
}

Write-Host "✅ 최신 파일 발견: $($latest.Name) (다운로드 시각: $($latest.LastWriteTime))" -ForegroundColor Green

# 2. 프로젝트 폴더의 main.py로 덮어쓰기
Copy-Item $latest.FullName ".\main.py" -Force
Write-Host "✅ main.py 덮어쓰기 완료" -ForegroundColor Green

# 3. git 반영
git pull
git add main.py
git commit -m "$commitMsg"
git push

# 4. 배포
fly deploy

# 5. 배포까지 다 성공했으면, Downloads 폴더의 옛날 main*.py 사본들 정리
#    (방금 쓴 최신 파일 1개만 남기고 나머지는 삭제)
if ($LASTEXITCODE -eq 0) {
    $toDelete = $downloadedFiles | Where-Object { $_.FullName -ne $latest.FullName }
    if ($toDelete) {
        $toDelete | Remove-Item -Force
        Write-Host "🧹 Downloads 폴더의 옛날 사본 $($toDelete.Count)개 정리 완료" -ForegroundColor Yellow
    }
    Write-Host "🎉 전체 완료: 덮어쓰기 → git push → fly deploy → 정리까지 끝났습니다." -ForegroundColor Cyan
} else {
    Write-Host "⚠️ fly deploy 단계에서 문제가 있었을 수 있습니다. 위 로그를 확인해주세요. (Downloads 정리는 건너뜁니다)" -ForegroundColor Red
}