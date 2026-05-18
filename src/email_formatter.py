"""EmailFormatter - Formats emails into raw Outlook-style HTML with embedded attachments."""

import re
import base64
from typing import Any, List, Optional, Tuple
from datetime import datetime


class AttachmentHandler:
    def __init__(self, config_manager: Optional[Any] = None):
        self._config = config_manager

    def _get_config(self, key: str, default: Any = None) -> Any:
        if self._config:
            return self._config.get(key, default)
        return default

    def _should_embed(self, attachment: Any) -> Tuple[bool, str]:
        try:
            size = getattr(attachment, 'Size', 0) or 0
            max_size_bytes = self._get_config("pdf.attachments.max_size_mb", 10) * 1024 * 1024
            if size > max_size_bytes:
                return False, f"exceeds size limit ({size / 1024 / 1024:.1f}MB > {max_size_bytes / 1024 / 1024:.0f}MB)"

            mime_type = 'application/octet-stream'
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
                        return False, f"file type blocked ({mime_type})"

            embed_types = self._get_config("pdf.attachments.embed_inline_types", [])
            if embed_types and isinstance(mime_type, str):
                for et in embed_types:
                    if et in mime_type:
                        return True, mime_type
                return False, f"file type not embeddable ({mime_type})"

            return False, "no embed rule configured"
        except Exception as e:
            return False, str(e)

    def _extract_attachment_data(self, attachment: Any) -> Optional[bytes]:
        try:
            return bytes(attachment.Binary)
        except Exception:
            try:
                import win32com.client
                stream = attachment.PropertyAccessor.GetProperty("http://schemas.microsoft.com/mapi/proptag/0x37010102")
                return bytes(stream)
            except Exception:
                return None

    def extract(self, email: Any) -> List[dict]:
        attachments = []
        try:
            if not hasattr(email, 'Attachments'):
                return attachments
            for i in range(1, email.Attachments.Count + 1):
                try:
                    attachment = email.Attachments.Item(i)
                    should_embed, reason = self._should_embed(attachment)
                    filename = getattr(attachment, 'FileName', '') or f'attachment_{i}'
                    size = getattr(attachment, 'Size', 0) or 0
                    mime_type = 'application/octet-stream'
                    try:
                        schema = "http://schemas.microsoft.com/mapi/proptag/0x370E001F"
                        mime_type = attachment.PropertyAccessor.GetProperty(schema)
                    except Exception:
                        pass
                    attachments.append({
                        'filename': filename,
                        'size': size,
                        'mime_type': mime_type,
                        'should_embed': should_embed,
                        'skip_reason': None if should_embed else reason,
                        'attachment': attachment,
                    })
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
            elif hasattr(sent_on, 'year') and hasattr(sent_on, 'month') and hasattr(sent_on, 'day'):
                dt = datetime(sent_on.year, sent_on.month, sent_on.day,
                             getattr(sent_on, 'hour', 0), getattr(sent_on, 'minute', 0))
            else:
                dt = datetime.fromisoformat(str(sent_on).split('+')[0])
            day_str = dt.strftime("%A, %B %d, %Y")
            time_str = dt.strftime("%I:%M %p").lstrip('0')
            return f"{day_str} {time_str}"
        except Exception:
            return str(sent_on)

    def _strip_html_outer_tags(self, html: str) -> str:
        content = html
        content = re.sub(r'<!DOCTYPE[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<html[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</html>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'<head[^>]*>.*?</head>', '', content, flags=re.IGNORECASE | re.DOTALL)
        content = re.sub(r'<body[^>]*>', '', content, flags=re.IGNORECASE)
        content = re.sub(r'</body>', '', content, flags=re.IGNORECASE)
        return content.strip()

    def format_email(self, email: Any, include_attachments: bool = True) -> str:
        sender_name = getattr(email, 'SenderName', '')
        sender_email = getattr(email, 'SenderEmailAddress', '')
        to_recipients = getattr(email, 'To', '')
        cc_recipients = getattr(email, 'CC', '')
        subject = getattr(email, 'Subject', '')
        html_body = getattr(email, 'HTMLBody', None)
        plain_body = getattr(email, 'Body', '')
        sent_on = getattr(email, 'SentOn', '')

        from_field = f"{sender_name} <{sender_email}>" if sender_email else sender_name
        sent_str = self._format_date(sent_on)

        header_html = (
            f'<div style="font-family: \'Calibri\', \'Arial\', sans-serif; font-size: 11pt; color: #000000; margin-bottom: 15px;">\n'
            f'    <p style="margin: 0; font-size: 16pt; font-weight: bold; color: #000000;">{sender_name}</p>\n'
            f'    <p style="margin: 5px 0 0 0;"><strong>From:</strong> {from_field}</p>\n'
            f'    <p style="margin: 0;"><strong>Sent:</strong> {sent_str}</p>\n'
            f'    <p style="margin: 0;"><strong>To:</strong> {to_recipients}</p>\n'
        )
        if cc_recipients and cc_recipients.strip():
            header_html += f'    <p style="margin: 0;"><strong>CC:</strong> {cc_recipients}</p>\n'
        header_html += (
            f'    <p style="margin: 0; margin-bottom: 10px;"><strong>Subject:</strong> {subject}</p>\n'
            f'</div>\n'
        )

        if html_body:
            body = f"{header_html}{self._strip_html_outer_tags(html_body)}"
        else:
            body = f"{header_html}<pre style=\"font-family: Calibri, Arial, sans-serif; font-size: 11pt;\">{plain_body}</pre>"

        if include_attachments:
            attachments_html = self._format_attachments(email)
            if attachments_html:
                body += attachments_html

        return f'<div class="email-container" style="page-break-inside: avoid; margin-bottom: 40px;">{body}</div>'

    def _format_attachments(self, email: Any) -> str:
        attachments = self._attachment_handler.extract(email)
        if not attachments:
            return ""

        html_parts = ['<div class="attachments-section" style="margin-top: 15px; padding: 10px; border: 1px solid #ccc; border-radius: 4px;">']
        html_parts.append('<p style="margin: 0 0 10px 0; font-weight: bold; font-size: 12pt;">Attachments</p>')

        embedded = []
        skipped = []

        for att in attachments:
            if att['should_embed'] and att['mime_type'].startswith('image/'):
                try:
                    data = self._attachment_handler._extract_attachment_data(att['attachment'])
                    if data:
                        b64 = base64.b64encode(data).decode('utf-8')
                        src = f"data:{att['mime_type']};base64,{b64}"
                        embedded.append(
                            f'<div style="margin-bottom: 10px;">'
                            f'<img src="{src}" alt="{att["filename"]}" style="max-width: 600px; height: auto; border: 1px solid #ddd; border-radius: 4px;" />'
                            f'<br/><span style="font-size: 10pt; color: #666;">{att["filename"]}</span>'
                            f'</div>'
                        )
                except Exception:
                    skipped.append(att['filename'])
            else:
                if att['skip_reason']:
                    reason_str = f" ({att['skip_reason']})" if att['skip_reason'] else ""
                    skipped.append(f"{att['filename']}{reason_str}")
                else:
                    skipped.append(att['filename'])

        for img_html in embedded:
            html_parts.append(img_html)

        if skipped:
            html_parts.append('<p style="margin: 5px 0; font-size: 10pt; color: #666;">Not embedded: ' + '; '.join(skipped) + '</p>')

        html_parts.append('</div>')
        return '\n'.join(html_parts)

    def format_multiple_emails(self, emails: List[Any]) -> str:
        html_parts = []
        for email in emails:
            email_html = self.format_email(email)
            html_parts.append(email_html)

        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Email Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        p {{ margin: 5px 0; }}
        hr {{ border: none; border-top: 1px solid #ccc; margin: 10px 0; }}
    </style>
</head>
<body>
{''.join(html_parts)}
</body>
</html>
"""