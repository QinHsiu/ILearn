# Soft-launch local smoke (Windows PowerShell)
$ErrorActionPreference = 'Stop'
$base = if ($env:ILEARN_SMOKE_BASE) { $env:ILEARN_SMOKE_BASE } else { 'http://127.0.0.1:8000' }
Write-Host "Smoke base: $base"

$h = Invoke-RestMethod "$base/healthz"
if ($h.status -ne 'ok') { throw "healthz failed" }
Write-Host "OK healthz"

$w = Invoke-RestMethod -Method Post -Uri "$base/waitlist" -ContentType 'application/json' -Body '{"email":"softlaunch@ilearn.local","role":"teacher"}'
if (-not $w.ok) { throw "waitlist failed" }
Write-Host "OK waitlist"

$demo = Invoke-RestMethod -Method Post -Uri "$base/demo/units/math_5_1/session"
$sid = $demo.session_id
Write-Host "OK demo $sid"

$ps = Invoke-RestMethod "$base/sessions/$sid/summary/parent"
if (-not $ps.action_summary) { throw "parent action_summary missing" }
Write-Host "OK parent action_summary"

$ts = Invoke-RestMethod "$base/sessions/$sid/summary/teacher"
if (-not $ts.tier_suggestion) { throw "tier_suggestion missing" }
Write-Host "OK teacher tier_suggestion"

$root = Invoke-WebRequest "$base/" -UseBasicParsing
if ($root.StatusCode -ne 200) { throw "landing failed" }
Write-Host "OK landing $($root.StatusCode)"

Write-Host "SOFT LAUNCH SMOKE PASSED"
