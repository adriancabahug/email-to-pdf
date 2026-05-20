"""EmailFormatter - Formats emails into raw Outlook-style HTML with embedded attachments."""

import base64
import re
from datetime import datetime
from typing import Any, List, Optional, Tuple


class AttachmentHandler:
    def __init__(self, config_manager: Optional[Any] = None):
        self._config = config_manager

    def _get_config(self, key: str, default: Any = None) -> Any:
        if self._config:
            return self._config.get(key, default)
        return default

    def _should_embed(self, attachment: Any) -> Tuple[bool, str]:
        try:
            size = getattr(attachment, "Size", 0) or 0
            max_size_bytes = (
                self._get_config("pdf.attachments.max_size_mb", 10) * 1024 * 1024
            )

            if size > max_size_bytes:
                return (
                    False,
                    f"exceeds size limit "
                    f"({size / 1024 / 1024:.1f}MB > "
                    f"{max_size_bytes / 1024 / 1024:.0f}MB)",
                )

            mime_type = "application/octet-stream"

            try:
                schema = "http://schemas.microsoft.com/mapi/proptag/0x370E001F"
                prop = attachment.PropertyAccessor.GetProperty(schema)

                if isinstance(prop, str):
                    mime_type = prop

            except Exception:
                pass

            skip_types = self._get_config("pdf.attachments.skip_types", [])

            if skip_types and isinstance(mime_type, str):
                for skip in skip_types:
                    if skip in mime_type:
                        return (False, f"file type blocked ({mime_type})")

            embed_types = self._get_config("pdf.attachments.embed_inline_types", [])

            if embed_types and isinstance(mime_type, str):
                for et in embed_types:
                    if et in mime_type:
                        return True, mime_type

                return (False, f"file type not embeddable ({mime_type})")

            return False, "no embed rule configured"

        except Exception as e:
            return False, str(e)

    def _extract_attachment_data(self, attachment: Any) -> Optional[bytes]:

        try:
            return bytes(attachment.Binary)

        except Exception:
            try:
                stream = attachment.PropertyAccessor.GetProperty(
                    "http://schemas.microsoft.com/mapi/proptag/0x37010102"
                )

                return bytes(stream)

            except Exception:
                return None

    def extract(self, email: Any) -> List[dict]:
        attachments = []

        try:
            if not hasattr(email, "Attachments"):
                return attachments

            for i in range(1, email.Attachments.Count + 1):
                try:
                    attachment = email.Attachments.Item(i)

                    should_embed, reason = self._should_embed(attachment)

                    filename = getattr(attachment, "FileName", "") or f"attachment_{i}"

                    size = getattr(attachment, "Size", 0) or 0

                    mime_type = "application/octet-stream"

                    try:
                        schema = "http://schemas.microsoft.com/mapi/proptag/0x370E001F"

                        mime_type = attachment.PropertyAccessor.GetProperty(schema)

                    except Exception:
                        pass

                    attachments.append(
                        {
                            "filename": filename,
                            "size": size,
                            "mime_type": mime_type,
                            "should_embed": should_embed,
                            "skip_reason": (None if should_embed else reason),
                            "attachment": attachment,
                        }
                    )

                except Exception:
                    pass

        except Exception:
            pass

        return attachments


class EmailFormatter:
    def __init__(self, config_manager: Optional[Any] = None):
        self._config = config_manager
        self._attachment_handler = AttachmentHandler(config_manager)

    def _format_date(self, sent_on: Any) -> str:
        if not sent_on:
            return ""

        try:
            if isinstance(sent_on, datetime):
                dt = sent_on

            elif hasattr(sent_on, "year"):
                dt = datetime(
                    sent_on.year,
                    sent_on.month,
                    sent_on.day,
                    getattr(sent_on, "hour", 0),
                    getattr(sent_on, "minute", 0),
                )

            else:
                dt = datetime.fromisoformat(str(sent_on).split("+")[0])

            return (
                f"{dt.strftime('%A, %B %d, %Y')} {dt.strftime('%I:%M %p').lstrip('0')}"
            )

        except Exception:
            return str(sent_on)

    def _strip_html_outer_tags(self, html: str) -> str:
        content = html

        content = re.sub(r"<!DOCTYPE[^>]*>", "", content, flags=re.IGNORECASE)

        content = re.sub(r"<html[^>]*>", "", content, flags=re.IGNORECASE)

        content = re.sub(r"</html>", "", content, flags=re.IGNORECASE)

        content = re.sub(
            r"<head[^>]*>.*?</head>", "", content, flags=re.IGNORECASE | re.DOTALL
        )

        content = re.sub(r"<body[^>]*>", "", content, flags=re.IGNORECASE)

        content = re.sub(r"</body>", "", content, flags=re.IGNORECASE)

        return content.strip()

    # -------------------------------------------------
    # CLASSIC OUTLOOK PRINT HEADER
    # -------------------------------------------------
    def _build_owa_header(self, subject, from_field, sent_str, to, cc, bcc):

        lines = [
            f"<p><b>From:</b> {from_field}</p>",
            f"<p><b>Sent:</b> {sent_str}</p>",
            f"<p><b>To:</b> {to}</p>",
        ]

        if cc:
            lines.append(f"<p><b>Cc:</b> {cc}</p>")

        if bcc:
            lines.append(f"<p><b>Bcc:</b> {bcc}</p>")

        lines.append(f"<p><b>Subject:</b> {subject}</p>")

        return f"""
<div class="owa-header">
    {"".join(lines)}
</div>

<hr>
"""

    def format_email(self, email: Any, include_attachments: bool = True) -> str:

        sender_name = getattr(email, "SenderName", "")
        sender_email = getattr(email, "SenderEmailAddress", "")

        to_recipients = getattr(email, "To", "")
        cc_recipients = getattr(email, "CC", "")
        bcc_recipients = getattr(email, "BCC", "")

        subject = getattr(email, "Subject", "")

        html_body = getattr(email, "HTMLBody", None)
        plain_body = getattr(email, "Body", "")

        sent_on = getattr(email, "SentOn", "")

        from_field = f"{sender_name} <{sender_email}>" if sender_email else sender_name

        sent_str = self._format_date(sent_on)

        header_html = self._build_owa_header(
            subject,
            from_field,
            sent_str,
            to_recipients,
            cc_recipients,
            bcc_recipients,
        )

        if html_body:
            body_content = self._strip_html_outer_tags(html_body)

        else:
            body_content = f"""
<div class="plain-text-body">
<pre>{plain_body}</pre>
</div>
"""

        attachments_html = ""

        if include_attachments:
            attachments_html = self._format_attachments(email)

        return f"""
<div class="owa-email-block" dir="ltr">

    {header_html}

    <div class="owa-body-content">
        {body_content}
    </div>

    {attachments_html}

</div>
"""

    def _format_attachments(self, email: Any) -> str:
        attachments = self._attachment_handler.extract(email)

        if not attachments:
            return ""

        html_parts = [
            '<div class="attachments-wrapper">',
            '<div class="attachments-title">Attachments</div>',
        ]

        for att in attachments:
            if att["should_embed"] and att["mime_type"].startswith("image/"):
                try:
                    data = self._attachment_handler._extract_attachment_data(
                        att["attachment"]
                    )

                    if data:
                        b64 = base64.b64encode(data).decode("utf-8")

                        src = f"data:{att['mime_type']};base64,{b64}"

                        html_parts.append(
                            f'''
<div class="attachment-image-block">
    <img src="{src}" />
    <div class="attachment-filename">
        {att["filename"]}
    </div>
</div>
'''
                        )

                except Exception:
                    pass

        html_parts.append("</div>")

        return "\n".join(html_parts)

    def format_multiple_emails(self, emails: List[Any]) -> str:

        def sort_key(e):
            t = getattr(e, "SentOn", None)

            if isinstance(t, datetime):
                return t

            try:
                return datetime.fromisoformat(str(t).split("+")[0])

            except Exception:
                return datetime.min

        emails = sorted(emails, key=sort_key)

        html_parts = []

        for email in emails:
            html_parts.append(self.format_email(email))

        return f"""
<!DOCTYPE html>
<html>

<head>
<meta charset="UTF-8">

<style>

html,
body {{
    margin: 0;
    padding: 0;
}}

body {{
    font-family:
        Aptos,
        Calibri,
        Helvetica,
        sans-serif;

    font-size: 11pt;
    line-height: 1.35;
    color: #000;
    background: #fff;

    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
}}

@page {{
    size: A4;
    margin: 14mm 12mm 14mm 12mm;
}}

/* ------------------------------------------------ */
/* EMAIL BLOCK                                      */
/* ------------------------------------------------ */

.owa-email-block {{
    width: 100%;
    box-sizing: border-box;

    margin: 0 0 18px 10px;
    padding: 0 0 18px 0;

    border-bottom: 1px solid #dcdcdc;

    page-break-inside: auto;
    break-inside: auto;
}}

.owa-email-block:not(:last-child) {{
    page-break-after: always;
    break-after: page;
}}

/* ------------------------------------------------ */
/* HEADER                                           */
/* ------------------------------------------------ */

.owa-header {{
    font-family:
        Aptos,
        Calibri,
        Helvetica,
        sans-serif;

    font-size: 11pt;
    line-height: 1.35;
    color: #000;
}}

.owa-header p {{
    margin: 0;
    padding: 0;
}}

/* ------------------------------------------------ */
/* BODY                                             */
/* ------------------------------------------------ */

.owa-body-content {{
    margin: 0;
    padding: 0;
}}

.elementToProof {{
    margin: 0;
    padding: 0;

    page-break-inside: auto;
    break-inside: auto;
}}

/* ------------------------------------------------ */
/* TABLES                                           */
/* ------------------------------------------------ */

table {{
    border-collapse: collapse;
    border-spacing: 0;

    max-width: 100% !important;

    page-break-inside: auto;
    break-inside: auto;
}}

tr,
td {{
    page-break-inside: avoid;
    break-inside: avoid;

    vertical-align: top;
}}

/* ------------------------------------------------ */
/* IMAGES                                           */
/* ------------------------------------------------ */

img {{
    max-width: 100% !important;
    height: auto !important;

    vertical-align: middle;
    border: 0;
}}

/* ------------------------------------------------ */
/* TEXT                                             */
/* ------------------------------------------------ */

p {{
    margin-top: 0;
    margin-bottom: 0;
}}

pre {{
    white-space: pre-wrap;
    word-wrap: break-word;

    margin: 0;

    font-family:
        Aptos,
        Calibri,
        Helvetica,
        sans-serif;

    font-size: 11pt;
}}

blockquote {{
    margin-left: 0;
    padding-left: 12px;
    border-left: 1px solid #ccc;
}}

/* ------------------------------------------------ */
/* HR                                               */
/* ------------------------------------------------ */

hr {{
    border: none;
    border-top: 1px solid #E1E1E1;
    margin: 10px 0;
}}

/* ------------------------------------------------ */
/* ATTACHMENTS                                      */
/* ------------------------------------------------ */

.attachments-wrapper {{
    margin-top: 14px;
}}

.attachments-title {{
    font-weight: bold;
    margin-bottom: 8px;
}}

.attachment-image-block {{
    margin-bottom: 12px;
}}

.attachment-image-block img {{
    max-width: 600px !important;
}}

.attachment-filename {{
    font-size: 10pt;
    color: #666;
    margin-top: 4px;
}}

/* ------------------------------------------------ */
/* OVERFLOW FIX                                     */
/* ------------------------------------------------ */

div {{
    overflow: visible !important;
}}

</style>

</head>

<body dir="ltr">

{"".join(html_parts)}

</body>
</html>
"""
