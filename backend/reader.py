from pathlib import Path

import fitz
import pytesseract
from docx import Document
from PIL import Image

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"



class AthenaReader:

    def read_pdf_text(self, file_path):

        document = fitz.open(file_path)

        text = ""

        for page in document:
            page_text = page.get_text()

            if page_text:
                text += page_text + "\n"

        return text


    def read_pdf_ocr(self, file_path):

        document = fitz.open(file_path)

        text = ""

        for page_number, page in enumerate(document):

            pix = page.get_pixmap(dpi=300)

            image_path = f"temp_page_{page_number}.png"

            pix.save(image_path)

            page_text = pytesseract.image_to_string(
                Image.open(image_path),
                lang="eng+ara"
            )

            text += page_text + "\n"

        return text


    def read_docx(self, file_path):

        document = Document(file_path)

        return "\n".join(
            p.text for p in document.paragraphs
        )


    def read(self, file_path):

        extension = Path(file_path).suffix.lower()

        if extension == ".pdf":

            text = self.read_pdf_text(file_path)

            if len(text.strip()) > 50:
                return text

            return self.read_pdf_ocr(file_path)

        if extension == ".docx":
            return self.read_docx(file_path)

        raise Exception(
            f"Unsupported file type {extension}"
        )