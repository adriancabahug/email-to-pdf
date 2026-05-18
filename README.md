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

### 3. Enter Director Details

After successful license validation, the tool will connect to Outlook and prompt you for director information:

\\\
First name: Mari
Last name: Acapulco
SMSF name: Sulianas SMSF
Email (optional): mari@eastcoastinc.com.au
\\\

- **First name** and **Last name** are required
- **SMSF name** is used for folder and file naming
- **Email** is optional — if left blank, the tool will search Outlook to find the director's email address automatically

### 4. Processing

The tool will:
1. Search all Outlook accounts and folders for emails involving the director
2. Format the emails into Outlook-style HTML
3. Generate a PDF file

You will see progress messages like:
\\\
Searching for emails involving mari@eastcoastinc.com.au...
Found 5 emails. Formatting...
Saving PDF for Sulianas SMSF...
PDF generated: C:\Users\admin\Documents\EmailPDFs\Sulianas SMSF\Mari Acapulco - Sulianas SMSF.pdf
\\\

### 5. Continue or Exit

After processing, you will be asked:
\\\
Process another director? (y/n):
\\\

- Type \y\ to process another director
- Type \
\ to exit the tool

## Where PDFs Are Saved

PDFs are saved to:
\\\
C:\Users\admin\Documents\EmailPDFs\{SMSF Name}\{First Last} - {SMSF Name}.pdf
\\\

Each SMSF gets its own folder, and the PDF is named after the director.

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

- Verify the director's email address is correct
- The tool searches all Outlook accounts and folders — if emails exist, they should be found

### PDF generation fails

- Ensure Playwright browsers are available (bundled with the EXE)
- Try running the tool as Administrator if permission errors occur

## Support

For license key issues or technical support, contact your administrator.
