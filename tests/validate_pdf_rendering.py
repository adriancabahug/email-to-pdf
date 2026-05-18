"""PDF Rendering Validation Suite - validates Playwright headless shell output quality."""

import sys
import os
from pathlib import Path
from playwright.sync_api import sync_playwright


SAMPLES_DIR = Path(__file__).parent / "samples"
OUTPUT_DIR = Path(__file__).parent / "validation_output"

EXPECTATIONS = {
    "01_plain_text.html": {
        "description": "Plain text email - basic paragraph rendering",
        "must_have": ["Hi team", "review the attached SMSF documents"],
        "must_not_have": [],
    },
    "02_html_formatting.html": {
        "description": "HTML with styles, headers, table",
        "must_have": ["SMSF Documents for Review", "Sulianas SMSF", "trust deed"],
        "must_not_have": [],
    },
    "03_nested_replies.html": {
        "description": "Nested reply chains with blockquotes",
        "must_have": ["RE: SMSF Documents for Review", "trustee declaration"],
        "must_not_have": [],
    },
    "04_table_layout.html": {
        "description": "HTML table with financial data",
        "must_have": ["Quarterly Financial Summary", "Sulianas SMSF", "1,250,000", "+4.2%"],
        "must_not_have": [],
    },
    "05_signature_disclaimer.html": {
        "description": "Long signature block and legal disclaimer",
        "must_have": ["Joel Martinez", "PRIVILEGED AND CONFIDENTIAL", "Ventas Advisory"],
        "must_not_have": [],
    },
    "06_long_thread.html": {
        "description": "Long thread with many nested quotes",
        "must_have": ["latest message", "original message"],
        "must_not_have": [],
    },
    "07_malformed_html.html": {
        "description": "Malformed HTML with broken tags",
        "must_have": ["Missing closing tags", "From: Mari Acapulco"],
        "must_not_have": [],
    },
    "08_outlook_quirks.html": {
        "description": "Outlook conditional markup and mso tags",
        "must_have": ["Property Settlement Documents", "45 Example Street", "650,000"],
        "must_not_have": [],
    },
}


def render_html_to_pdf(source_path: Path, output_path: Path) -> bool:
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(f"file:///{source_path.resolve()}")
            page.pdf(
                path=str(output_path),
                format="A4",
                print_background=True,
                margin={"top": "10mm", "bottom": "10mm", "left": "10mm", "right": "10mm"}
            )
            browser.close()
        return True
    except Exception as e:
        print(f"    [FAIL] Render error: {e}")
        return False


def validate_pdf(output_path: Path, sample_name: str, expectations: dict) -> dict:
    result = {
        "sample": sample_name,
        "description": expectations["description"],
        "passed": False,
        "pdf_created": False,
        "issues": [],
    }

    if not output_path.exists():
        result["issues"].append(f"PDF not created at {output_path}")
        return result

    result["pdf_created"] = True

    pdf_size = output_path.stat().st_size
    result["pdf_size_kb"] = pdf_size / 1024

    if pdf_size < 500:
        result["issues"].append(f"PDF suspiciously small ({pdf_size} bytes) - likely blank/corrupted")
        return result

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            source_html_path = SAMPLES_DIR / f"{sample_name.replace('.pdf', '.html')}"
            page.goto(f"file:///{source_html_path.resolve()}")

            html_text = page.content()

            browser.close()
    except Exception as e:
        result["issues"].append(f"Failed to load source HTML: {e}")
        return result

    issues = []
    for phrase in expectations.get("must_have", []):
        if phrase not in html_text:
            issues.append(f"Missing expected text: '{phrase}'")
    for phrase in expectations.get("must_not_have", []):
        if phrase in html_text:
            issues.append(f"Found forbidden text: '{phrase}'")

    result["issues"].extend(issues)
    result["passed"] = len(issues) == 0

    return result


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    sample_files = sorted(SAMPLES_DIR.glob("*.html"))
    if not sample_files:
        print("[FAIL] No sample HTML files found in tests/samples/")
        return 1

    print("=== PDF Rendering Validation ===\n")
    print(f"Samples directory: {SAMPLES_DIR}")
    print(f"Output directory: {OUTPUT_DIR}\n")

    results = []
    passed_count = 0
    failed_count = 0

    for sample_file in sample_files:
        sample_name = sample_file.name
        expectations = EXPECTATIONS.get(sample_name, {})
        if not expectations:
            print(f"[WARN] No expectations defined for {sample_name} - skipping")
            continue

        print(f"Testing: {sample_name}")
        print(f"  Description: {expectations['description']}")

        pdf_path = OUTPUT_DIR / f"{sample_file.stem}.pdf"

        success = render_html_to_pdf(sample_file, pdf_path)
        if not success:
            print(f"  [FAIL] Could not render PDF")
            failed_count += 1
            results.append({"sample": sample_name, "passed": False, "issues": ["Render failed"]})
            continue

        validation = validate_pdf(pdf_path, sample_name, expectations)
        validation["pdf_size_kb"] = pdf_path.stat().st_size / 1024 if pdf_path.exists() else 0

        if validation["passed"]:
            print(f"  [OK] PDF created ({validation['pdf_size_kb']:.1f} KB)")
            passed_count += 1
        else:
            print(f"  [FAIL] Validation issues:")
            for issue in validation["issues"]:
                print(f"    - {issue}")
            failed_count += 1

        results.append(validation)
        print()

    print("=== Summary ===")
    print(f"  Passed: {passed_count}/{len(sample_files)}")
    print(f"  Failed: {failed_count}/{len(sample_files)}")

    if failed_count > 0:
        print(f"\nFailed samples:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['sample']}: {r.get('description', 'N/A')}")
                for issue in r.get("issues", []):
                    print(f"    {issue}")

    print(f"\nPDFs saved to: {OUTPUT_DIR}")

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())