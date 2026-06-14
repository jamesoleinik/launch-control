# Send-Q3TriggerEmails.ps1
# Sends the two Episode 7 Part 2 trigger emails to the on-camera
# demo mailbox (Setup B from the README appendix), using Microsoft
# Graph PowerShell with interactive consent.
#
# Why this exists alongside scripts/send_q3_trigger_emails.py:
#   The Python version uses AzureCliCredential, which gets a 403
#   on Mail.Send because the Azure CLI public client app isn't
#   preconsented for /Mail.Send on this tenant.
#   Connect-MgGraph uses the Microsoft Graph PowerShell first-party
#   client which IS able to ask for Mail.Send interactively.
#
# Usage (from repo root):
#   pwsh -File scripts/send_q3_trigger_emails.ps1
#
# First run will pop a browser asking you to consent to "Send mail
# as you (Mail.Send)" for jamesol@a365preview001.onmicrosoft.com.
# Subsequent runs reuse the cached token until it expires.

$ErrorActionPreference = 'Stop'

$Recipient = 'jamesol@a365preview001.onmicrosoft.com'

$Emails = @(
    @{
        Subject = 'Q3 Widget Launch - export to CSV crashes the app for Northwind'
        BodyLines = @(
            'Q3 Widget Launch field report from Northwind.',
            'Northwind hit a hard crash on Export to CSV with a large widget composition (about 14 widgets on one canvas). The export spinner runs for roughly 30 seconds and then the app crashes back to the home screen. They lose unsaved work.',
            'Repro is consistent on their tenant. Severity from their side: blocker for the Q3 rollout. Attached PDF has the customer''s repro notes verbatim.'
        )
        Attachment = 'Q3-widget-export-crash-northwind.pdf'
        Role = 'ENRICH (overlaps the seeded export-crash baseline task)'
    },
    @{
        Subject = 'Q3 Widget Launch - mobile auth callback fails after SSO'
        BodyLines = @(
            'Q3 Widget Launch issue from mobile beta cohort.',
            'Mobile users on the Q3 Widget Launch beta build cannot complete sign-in. After the IdP redirect the OAuth callback returns a 500 and the app drops the user back at the login screen. Reproduced on iOS and Android in the same build.',
            'No existing task on the launch covers this. Filed via this email so the morning sweep picks it up. Attached PDF has the device matrix and the exact callback URL that 500s.'
        )
        Attachment = 'Q3-widget-mobile-auth-callback.pdf'
        Role = 'NEW TASK (no existing task on the launch covers this)'
    }
)

function New-PdfBytes {
    param([string]$Title, [string[]]$Paragraphs)
    $tmp = [System.IO.Path]::GetTempFileName() + '.pdf'
    $py = @"
import sys
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
out = sys.argv[1]
title = sys.argv[2]
paragraphs = sys.argv[3:]
doc = SimpleDocTemplate(out, pagesize=LETTER, title=title)
s = getSampleStyleSheet()
story = [Paragraph(title, s["Title"]), Spacer(1, 12)]
for p in paragraphs:
    story.append(Paragraph(p, s["BodyText"]))
    story.append(Spacer(1, 8))
doc.build(story)
"@
    $pyfile = [System.IO.Path]::GetTempFileName() + '.py'
    Set-Content -Path $pyfile -Value $py -Encoding utf8
    & python $pyfile $tmp $Title @Paragraphs | Out-Null
    Remove-Item $pyfile -Force
    $bytes = [System.IO.File]::ReadAllBytes($tmp)
    Remove-Item $tmp -Force
    return $bytes
}

Import-Module Microsoft.Graph.Authentication
$ctx = Get-MgContext
if (-not $ctx -or $ctx.Scopes -notcontains 'Mail.Send') {
    Write-Host 'Connecting to Microsoft Graph (Mail.Send scope) ...'
    Connect-MgGraph -Scopes 'Mail.Send' -NoWelcome | Out-Null
    $ctx = Get-MgContext
}
Write-Host "Connected as $($ctx.Account)"

foreach ($e in $Emails) {
    Write-Host "  -> $($e.Subject)"
    Write-Host "       ($($e.Role))"

    $pdf = New-PdfBytes -Title $e.Subject -Paragraphs $e.BodyLines
    $b64 = [Convert]::ToBase64String($pdf)
    $bodyHtml = ($e.BodyLines | ForEach-Object { "<p>$_</p>" }) -join '<br/><br/>'

    $body = @{
        message = @{
            subject = $e.Subject
            body = @{ contentType = 'HTML'; content = $bodyHtml }
            toRecipients = @(@{ emailAddress = @{ address = $Recipient } })
            attachments = @(
                @{
                    '@odata.type' = '#microsoft.graph.fileAttachment'
                    name = $e.Attachment
                    contentType = 'application/pdf'
                    contentBytes = $b64
                }
            )
        }
        saveToSentItems = $true
    } | ConvertTo-Json -Depth 8

    Invoke-MgGraphRequest `
        -Method POST `
        -Uri 'https://graph.microsoft.com/v1.0/me/sendMail' `
        -Body $body `
        -ContentType 'application/json' | Out-Null
    Write-Host "     sent ($($pdf.Length) byte PDF attached)"
}

Write-Host ''
Write-Host "Done. Both trigger emails are in $Recipient's inbox."
Write-Host 'Allow ~1-2 minutes for Outlook indexing before running Step 2b.'
