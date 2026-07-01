$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$yearDir = Split-Path -Parent $scriptDir
$repoRoot = Split-Path -Parent $yearDir
Set-Location $repoRoot

$reportDir = Join-Path $yearDir "05_delivery"
$songti = ([char]0x5B8B).ToString() + ([char]0x4F53).ToString()

python (Join-Path $scriptDir "generate_csust_report.py")
if ($LASTEXITCODE -ne 0) {
    throw "generate_csust_report.py failed with exit code $LASTEXITCODE"
}

$docxItem = Get-ChildItem -LiteralPath $reportDir -Filter "*.docx" |
    Where-Object { -not $_.Name.StartsWith("~$") } |
    Sort-Object Length -Descending |
    Select-Object -First 1
if (-not $docxItem) {
    throw "Generated DOCX was not found."
}
$docx = $docxItem.FullName
$pdf = [System.IO.Path]::ChangeExtension($docx, ".pdf")

$word = $null
$doc = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($docx, $false, $false)

    if ($doc.TablesOfContents.Count -gt 0) {
        $toc = $doc.TablesOfContents.Item(1)
        $toc.Update()

        $range = $toc.Range
        $range.Font.Name = "Times New Roman"
        $range.Font.NameFarEast = $songti
        $range.Font.Size = 10.5
        $range.ParagraphFormat.LineSpacingRule = 4
        $range.ParagraphFormat.LineSpacing = 13
        $range.ParagraphFormat.SpaceBefore = 0
        $range.ParagraphFormat.SpaceAfter = 0

        $doc.Repaginate()
        $toc.UpdatePageNumbers()

        $range = $toc.Range
        $range.Font.Name = "Times New Roman"
        $range.Font.NameFarEast = $songti
        $range.Font.Size = 10.5
        $range.ParagraphFormat.LineSpacingRule = 4
        $range.ParagraphFormat.LineSpacing = 13
        $range.ParagraphFormat.SpaceBefore = 0
        $range.ParagraphFormat.SpaceAfter = 0
    }

    foreach ($section in $doc.Sections) {
        foreach ($footer in $section.Footers) {
            foreach ($field in $footer.Range.Fields) {
                $field.Update() | Out-Null
            }
        }
    }

    $doc.Save()
}
finally {
    if ($doc -ne $null) {
        $doc.Close($false) | Out-Null
    }
    if ($word -ne $null) {
        $word.Quit() | Out-Null
    }
}

$soffice = (Get-Command soffice -ErrorAction SilentlyContinue).Source
if (-not $soffice -and (Test-Path "C:\Program Files\LibreOffice\program\soffice.exe")) {
    $soffice = "C:\Program Files\LibreOffice\program\soffice.exe"
}
if (-not $soffice) {
    throw "LibreOffice soffice.exe was not found."
}

if (Test-Path -LiteralPath $pdf) {
    Remove-Item -LiteralPath $pdf -Force
}
& $soffice --headless --convert-to pdf --outdir $reportDir $docx | Out-Null
if (-not (Test-Path -LiteralPath $pdf)) {
    throw "PDF export failed."
}

$lockFiles = Get-ChildItem -LiteralPath $reportDir -Filter "~$*.docx" -ErrorAction SilentlyContinue
foreach ($file in $lockFiles) {
    Remove-Item -LiteralPath $file.FullName -Force
}

$pdftoppm = Get-Command pdftoppm -ErrorAction SilentlyContinue
if ($pdftoppm) {
    $renderDir = Join-Path $repoRoot "tmp\pdfs\csust_report_final"
    New-Item -ItemType Directory -Force -Path $renderDir | Out-Null
    Get-ChildItem -LiteralPath $renderDir -Filter "page-*.png" -ErrorAction SilentlyContinue | Remove-Item -Force
    & $pdftoppm.Source -png -r 140 $pdf (Join-Path $renderDir "page") | Out-Null
}

Get-Item -LiteralPath $docx, $pdf | Select-Object Name, Length, LastWriteTime
