import io
import re
import shutil
from typing import Tuple, Optional, List
from app.core.logging import logger

class DocumentParsingError(Exception):
    """Base exception for document parsing errors."""
    pass

class DocumentUnsupportedError(DocumentParsingError):
    """Raised when file extension or format is unsupported."""
    pass

class DocumentEmptyError(DocumentParsingError):
    """Raised when document content is empty or contains no text."""
    pass

class DocumentCorruptedError(DocumentParsingError):
    """Raised when document format is corrupt or unreadable."""
    pass

class DocumentEncryptedError(DocumentParsingError):
    """Raised when document is password-protected or encrypted."""
    pass

class DocumentScannedError(DocumentParsingError):
    """Raised when document is a scanned image and OCR is required."""
    def __init__(self, message: str, ocr_available: bool = False):
        super().__init__(message)
        self.ocr_available = ocr_available


class DocumentParser:
    """Extracts and normalizes text from PDF and DOCX files with diagnostic error handling."""

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS = {".pdf", ".docx"}

    @classmethod
    def is_ocr_available(cls) -> bool:
        """Check if pytesseract and the system tesseract binary are available."""
        try:
            import pytesseract
            has_binary = shutil.which("tesseract") is not None
            return has_binary
        except Exception:
            return False

    @classmethod
    def validate_file(cls, filename: str, content: bytes) -> Tuple[bool, Optional[str]]:
        """Validate file name, extension, size, and magic bytes."""
        if not filename or not filename.strip():
            return False, "File name is required."

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in cls.ALLOWED_EXTENSIONS:
            return False, f"Unsupported file extension '{ext}'. Only PDF and DOCX files are allowed."

        if not content or len(content) == 0:
            return False, "The uploaded file is empty (0 bytes)."

        if len(content) > cls.MAX_FILE_SIZE:
            return False, f"File exceeds maximum allowed size of {cls.MAX_FILE_SIZE // (1024*1024)}MB."

        # Validate magic headers
        if ext == ".pdf" and not content.startswith(b"%PDF"):
            return False, "Invalid PDF file structure. Missing standard PDF file signature."
        elif ext == ".docx" and not content.startswith(b"PK\x03\x04"):
            return False, "Invalid DOCX file structure. Document must be a valid OpenXML package."

        return True, None

    @classmethod
    def extract_text_from_pdf(cls, content: bytes) -> str:
        """
        Extracts text from PDF document.
        Distinguishes encrypted, corrupted, scanned, and text-based PDFs.
        """
        # 1. Structural and encryption check via pypdf
        has_images = False
        reader = None
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            if reader.is_encrypted:
                try:
                    # Attempt empty password decrypt
                    decrypted = reader.decrypt("")
                    if not decrypted:
                        raise DocumentEncryptedError(
                            "The PDF document is password-protected or encrypted. Please upload an unencrypted document."
                        )
                except Exception:
                    raise DocumentEncryptedError(
                        "The PDF document is password-protected or encrypted. Please upload an unencrypted document."
                    )
        except DocumentEncryptedError:
            raise
        except Exception as e:
            logger.warning(f"pypdf reader initialization failed: {e}")
            # If pypdf failed, might be corrupted
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(content)) as check_pdf:
                    pass
            except Exception as e2:
                raise DocumentCorruptedError(
                    f"The PDF file is corrupted or improperly formatted: {e2}"
                )

        # 2. Extract text using pdfplumber first (best layout preservation)
        extracted_text = ""
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                if len(pdf.pages) == 0:
                    raise DocumentEmptyError("The PDF document contains no pages.")
                pages_text = []
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                    if hasattr(page, "images") and len(page.images) > 0:
                        has_images = True
                extracted_text = "\n".join(pages_text)
        except (DocumentEmptyError, DocumentEncryptedError):
            raise
        except Exception as e:
            logger.warning(f"pdfplumber extraction encounter: {e}")

        # 3. Fallback to pypdf if pdfplumber extracted nothing
        if not extracted_text.strip() and reader:
            try:
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                    if hasattr(page, "images") and len(page.images) > 0:
                        has_images = True
                extracted_text = "\n".join(pages_text)
            except Exception as e:
                logger.warning(f"pypdf page extraction encounter: {e}")

        normalized = cls.normalize_text(extracted_text)

        # 4. If meaningful text exists (at least 15 alphanumeric characters), return it
        alphanumeric_count = len(re.findall(r"[A-Za-z0-9]", normalized))
        if alphanumeric_count >= 15:
            return normalized

        # 5. Handle scanned document or empty PDF
        ocr_available = cls.is_ocr_available()
        if ocr_available:
            ocr_text = cls._attempt_ocr(content)
            if ocr_text and len(re.findall(r"[A-Za-z0-9]", ocr_text)) >= 15:
                return ocr_text

        # Scanned vs Empty classification
        if has_images or (reader and len(reader.pages) > 0):
            raise DocumentScannedError(
                "The uploaded PDF appears to be a scanned document or image without a readable text layer. "
                "Optical Character Recognition (OCR) is required to process scanned files, but OCR is currently not available in this environment. "
                "Please upload a standard text-based PDF or Word (.docx) document.",
                ocr_available=ocr_available
            )
        else:
            raise DocumentEmptyError("The document contains no readable text or content.")

    @classmethod
    def _attempt_ocr(cls, content: bytes) -> str:
        """Attempt OCR using pytesseract and pypdfium2/pillow if available."""
        try:
            import pytesseract
            import pypdfium2
            pdf = pypdfium2.PdfDocument(content)
            pages_text = []
            for i in range(len(pdf)):
                page = pdf[i]
                image = page.render(scale=2).to_pil()
                text = pytesseract.image_to_string(image)
                if text:
                    pages_text.append(text)
            return cls.normalize_text("\n".join(pages_text))
        except Exception as e:
            logger.warning(f"OCR execution failed: {e}")
            return ""

    @classmethod
    def extract_text_from_docx(cls, content: bytes) -> str:
        """Extracts text from DOCX file, handling corruption and empty documents."""
        try:
            import docx
            doc = docx.Document(io.BytesIO(content))
        except Exception as e:
            raise DocumentCorruptedError(
                f"The DOCX document is corrupted or not a valid Word document package: {e}"
            )

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    if cell.text.strip():
                        paragraphs.append(cell.text.strip())

        text = "\n".join(paragraphs)
        normalized = cls.normalize_text(text)

        if not normalized or len(re.findall(r"[A-Za-z0-9]", normalized)) < 5:
            raise DocumentEmptyError("The uploaded DOCX document contains no readable text.")

        return normalized

    @classmethod
    def normalize_text(cls, text: str) -> str:
        if not text:
            return ""
        # Replace non-breaking spaces and clean whitespace
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        return text.strip()

    @classmethod
    def extract_text(cls, filename: str, content: bytes) -> str:
        """Validates and extracts normalized text from supported document types."""
        is_valid, err = cls.validate_file(filename, content)
        if not is_valid:
            if "Unsupported file extension" in (err or ""):
                raise DocumentUnsupportedError(err)
            elif "empty" in (err or ""):
                raise DocumentEmptyError(err)
            else:
                raise DocumentCorruptedError(err)

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext == ".pdf":
            return cls.extract_text_from_pdf(content)
        elif ext == ".docx":
            return cls.extract_text_from_docx(content)
        else:
            raise DocumentUnsupportedError(f"Unsupported file format '{ext}'.")
