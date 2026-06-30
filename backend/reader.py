from pathlib import Path
from pypdf import PdfReader
from docx import Document


class AthenaReader:

    def read_pdf(self, file_path):

        reader = PdfReader(file_path)

        text = ""

        for page in reader.pages:
            page_text = page.extract_text()

            if page_text:
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
            return self.read_pdf(file_path)

        if extension == ".docx":
            return self.read_docx(file_path)

        raise Exception(
            f"Unsupported file type {extension}"
        )
