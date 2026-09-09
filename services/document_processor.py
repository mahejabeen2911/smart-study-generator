"""
Document Processor
Extracts plain text from PDF, TXT, and image files.
"""

import os


class DocumentProcessor:
    """Handles text extraction from supported file types."""

    # Maximum characters to extract (prevents token overflow downstream)
    MAX_CHARS = 15000

    def extract_text(self, filepath: str, extension: str) -> str:
        """
        Extract text from the given file.

        Parameters
        ----------
        filepath  : Absolute path to the saved file.
        extension : Lowercase file extension without the dot (e.g. 'pdf').

        Returns
        -------
        Extracted plain text (str).
        """
        ext = extension.lower().strip(".")

        if ext == "pdf":
            return self._extract_pdf(filepath)
        elif ext == "txt":
            return self._extract_txt(filepath)
        elif ext in {"jpg", "jpeg", "png"}:
            return self._extract_image(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    # ── Private helpers ───────────────────────────────────────────────────────

    def _extract_pdf(self, filepath: str) -> str:
        """Extract text from a PDF using pypdf."""
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ImportError(
                "pypdf is required for PDF processing. Run: pip install pypdf"
            )

        reader = PdfReader(filepath)
        pages_text = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)
            # Stop early if we already have plenty of text
            if sum(len(t) for t in pages_text) >= self.MAX_CHARS:
                break

        text = "\n\n".join(pages_text).strip()
        if not text:
            raise ValueError(
                "No readable text found in the PDF. "
                "The file may be scanned or image-based."
            )
        return text[: self.MAX_CHARS]

    def _extract_txt(self, filepath: str) -> str:
        """Read a plain-text file, trying UTF-8 then Latin-1."""
        for encoding in ("utf-8", "latin-1"):
            try:
                with open(filepath, "r", encoding=encoding) as fh:
                    return fh.read()[: self.MAX_CHARS]
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode the text file. Please save it as UTF-8.")

    def _extract_image(self, filepath: str) -> str:
        """
        Basic image-to-text via pytesseract (optional).
        Returns a helpful message if Tesseract is not installed.
        """
        try:
            from PIL import Image
            import pytesseract

            img = Image.open(filepath)
            text = pytesseract.image_to_string(img)
            if not text.strip():
                return (
                    "[Image uploaded but no text could be extracted. "
                    "Please ensure the image contains clear, readable text.]"
                )
            return text.strip()[: self.MAX_CHARS]

        except ImportError:
            return (
                "[Image OCR requires Pillow and pytesseract. "
                "Install them or paste your notes as text instead.]"
            )
        except Exception as exc:
            return f"[Image processing failed: {exc}. Please paste your notes as text instead.]"
