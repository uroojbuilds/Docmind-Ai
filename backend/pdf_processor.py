import os


class PDFProcessor:
    def __init__(self, chunk_size=500, overlap=50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, file_path: str, source_name: str) -> list:
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            text = self._read_pdf(file_path)
        elif ext in [".txt", ".md"]:
            text = self._read_text(file_path)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        print(f"Extracted text length: {len(text)} characters")  # DEBUG
        chunks = self._split_into_chunks(text)
        print(f"Total chunks created: {len(chunks)}")  # DEBUG

        return [{"text": chunk, "source": source_name} for chunk in chunks]

    def _read_pdf(self, file_path: str) -> str:
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(file_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                        print(f"Page {i+1}: {len(page_text)} chars extracted")  # DEBUG
                    else:
                        print(f"Page {i+1}: NO TEXT FOUND")  # DEBUG
            return text
        except ImportError:
            raise ImportError("Install pdfplumber: pip install pdfplumber")

    def _read_text(self, file_path: str) -> str:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def _split_into_chunks(self, text: str) -> list:
        words = text.split()
        chunks = []

        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + self.chunk_size])
            if chunk.strip():
                chunks.append(chunk)
            i += self.chunk_size - self.overlap

        return chunks