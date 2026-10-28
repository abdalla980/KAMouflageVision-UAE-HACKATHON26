# Exports KAMouflage_Vision_Pitch.pptx to PDF with PowerPoint. Run: powershell -File export_pdf.ps1
$pptx = Join-Path $PSScriptRoot "KAMouflage_Vision_Pitch.pptx"
$pdf = Join-Path $PSScriptRoot "KAMouflage_Vision_Pitch.pdf"
$app = New-Object -ComObject PowerPoint.Application
try {
    $deck = $app.Presentations.Open($pptx, $true, $false, $false)
    $deck.SaveAs($pdf, 32)
    $deck.Close()
    "wrote $pdf"
} finally {
    $app.Quit()
}
