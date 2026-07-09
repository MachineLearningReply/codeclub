import io

from anyio import open_file
from pdf_oxide import AsyncPdfDocument

from .interface import ContentT, Document, FileT, NoContentFoundError, Page, ParserConfig


class PDFParser:
    def __init__(self, config: ParserConfig | None = None) -> None:
        self.config = config or {
            "extract_tables": True,
            "extract_images": True,
        }

    async def parse_bytes(self, content: ContentT) -> Document:
        if isinstance(content, io.BytesIO):
            content = content.read()

        parsed = await AsyncPdfDocument.from_bytes(content)
        pages = []
        for i, page in enumerate(parsed.doc):
            if page is None:
                raise NoContentFoundError
            images = parsed.doc.extract_images(i)
            tables = parsed.doc.extract_tables(i)

            pages.append(Page(page.text, page.markdown(detect_headings=True), images, tables))

        return Document(pages)

    async def parse_file(self, file_path: FileT) -> Document:
        async_file = await open_file(file_path)
        content = await async_file.read1()  # ty: ignore
        return await self.parse_bytes(content)
