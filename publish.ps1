param(
    [string]$Message = 'Update ANN JAM Force JST',
    [string]$AuthorName,
    [string]$AuthorEmail,
    [switch]$Preview
)
$ErrorActionPreference = 'Stop'
$taskPublishArgs = @(
    (Join-Path $PSScriptRoot 'tools\publish.py'),
    '--message', $Message
)
if ($AuthorName) { $taskPublishArgs += @('--author-name', $AuthorName) }
if ($AuthorEmail) { $taskPublishArgs += @('--author-email', $AuthorEmail) }
if ($Preview) { $taskPublishArgs += '--preview' }
& python @taskPublishArgs
if ($LASTEXITCODE -ne 0) { throw "Publish failed: $LASTEXITCODE" }
