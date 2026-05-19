# Email to PDF Automation Tool - User Guide

## Overview

This tool extracts email correspondence between directors and staff from Microsoft Outlook and generates PDF files that look like Outlook's native print/export.

## Prerequisites

- **Microsoft Outlook** must be installed, open, and logged in
- **Internet connection** is required (for license validation on first launch)
- **Windows 10 or later**

## Getting Started

### 1. Launch the Application

Double-click \email-to-pdf.exe\ to start the tool.

### 2. Enter Your License Key

On first launch, you will be prompted to enter your license key:

\\\
Enter your license key:
\\\

Type or paste the key provided to you and press Enter. The key will be validated automatically and saved for future use.

> **Note:** License keys have an expiration date. If your key expires, you will be prompted to enter a new one.

### 3. Enter SMSF Details

After successful license validation, the tool will connect to Outlook and prompt you for SMSF information:

\\
SMSF name: Aura Super
Emails/keywords (comma-separated or one per line, blank to finish):
> andy.studt74@gmail.com
> annaderdowski@uahoo.com
> ventas
> exceedia
> shapesuper
> earlypay
> newwavelaw
>
Date range: [1] This year (default), [2] Custom range
> 1
\\

- **SMSF name** is used for folder and file naming
- **Emails/keywords** can be email addresses or search terms (one per line or comma-separated). Leave blank and press Enter when done.
- **Date range** lets you search emails from this year or a custom date range

### 4. Processing

The tool will:
1. Search all Outlook accounts and folders for emails matching the keywords
2. Format the emails into Outlook-style HTML
3. Generate a PDF file

You will see progress messages like:
\\
Searching for emails matching keywords...
Found 42 emails in 8 folders. Formatting...
Saving PDF for Aura Super...
PDF generated: C:\Users\admin\Documents\EmailPDFs\Aura Super\Aura Super - Email Export.pdf
\\

### 5. Continue or Exit

After processing, you will be asked:
\\
Process another SMSF? (y/n):
\\

- Type \y\ to process another SMSF
- Type \ to exit the tool

## Where PDFs Are Saved

PDFs are saved to:
\\
C:\Users\admin\Documents\EmailPDFs\{SMSF}\{SMSF} - Email Export.pdf
\\

Each SMSF gets its own folder, and the PDF is named after the SMSF.

## Troubleshooting

### "Unable to validate license. Check your internet connection"

- Ensure you have an active internet connection
- The tool requires internet access to validate the license key on first launch and periodically thereafter

### "Your license key has expired"

- Contact your administrator for a new license key

### "Failed to connect to Outlook"

- Ensure Microsoft Outlook is open and logged in
- The tool requires Outlook to be running to access emails

### "No emails found"

- Verify the search keywords are correct
- The tool searches all Outlook accounts and folders — if emails exist, they should be found
- Try different keywords or email addresses

### PDF generation fails

- Ensure Playwright browsers are available (bundled with the EXE)
- Try running the tool as Administrator if permission errors occur

## Support

For license key issues or technical support, contact your administrator.
