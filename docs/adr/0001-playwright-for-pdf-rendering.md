# Playwright + Chromium for PDF rendering

Email bodies are raw HTML — often malformed Outlook/Exchange HTML with MSO-specific markup, VML, conditional comments, and deeply nested tables. The only way to render these with pixel-perfect fidelity is a real browser engine. Lighter alternatives (wkhtmltopdf, weasyprint, Typst + custom HTML-to-Typst converter) all produce visible formatting differences on real-world email HTML and were rejected. The 86MB Chromium overhead in the bundle is accepted as the cost of correctness.
