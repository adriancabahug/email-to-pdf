"""FileManager - Creates folders and saves PDFs with proper naming"""

from pathlib import Path
from typing import Optional, Union

from src.pdf_generator import PDFGenerator
from src.email_formatter import EmailFormatter


class FileManager:
    """Manages file output: folder creation and PDF saving"""

    DEFAULT_OUTPUT_BASE = Path(r"C:\Users\admin\Documents\EmailPDFs")

    def __init__(
        self,
        output_base: Optional[Union[str, Path]] = None,
        pdf_generator: Optional[PDFGenerator] = None,
        email_formatter: Optional[EmailFormatter] = None,
    ):
        self.output_base = Path(output_base) if output_base else self.DEFAULT_OUTPUT_BASE
        self.pdf_generator = pdf_generator if pdf_generator is not None else PDFGenerator()
        self.email_formatter = email_formatter if email_formatter is not None else EmailFormatter()

    def get_output_base(self) -> Path:
        """Get the base output directory"""
        return self.output_base

    def generate_filename(self, first_name: str, last_name: str, smsf_name: str) -> str:
        """Generate filename in format: {First Last} - {SMSF}.pdf"""
        full_name = f"{first_name} {last_name}"
        smsf = smsf_name if smsf_name else ""
        return f"{full_name} - {smsf}.pdf"

    def create_smsf_folder(self, smsf_name: str) -> Path:
        """Create folder for SMSF. Returns folder path as Path."""
        folder_path = self.output_base / smsf_name
        folder_path.mkdir(parents=True, exist_ok=True)
        return folder_path

    def get_full_path(self, smsf_name: str, filename: str) -> Path:
        """Get full file path including folder and filename."""
        return self.output_base / smsf_name / filename

    def ensure_folder_exists(self, folder_path: Union[str, Path]) -> bool:
        """Ensure folder exists, create if it doesn't."""
        try:
            Path(folder_path).mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Error creating folder: {e}")
            return False

    def save_pdf(
        self,
        html_content: str,
        first_name: str,
        last_name: str,
        smsf_name: str,
    ) -> Optional[str]:
        """
        Save PDF to appropriate folder.
        Returns full path string if successful, None otherwise.
        """
        try:
            filename = self.generate_filename(first_name, last_name, smsf_name)
            self.create_smsf_folder(smsf_name)
            full_path = self.get_full_path(smsf_name, filename)

            # Pass Path object to PDFGenerator (it expects pathlib.Path)
            success = self.pdf_generator.generate_pdf(html_content, full_path)

            if success:
                return str(full_path)
            return None

        except Exception as e:
            print(f"Error saving PDF: {e}")
            return None
