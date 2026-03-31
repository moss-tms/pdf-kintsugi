# pdf-kintsugi

**pdf-kintsugi** is a Python library that PDF table extraction and text recovery by combining the high-level document understanding of **Docling** with the precise, character-level bounding box analysis of **pdfplumber**.

Like the Japanese art of *kintsugi* (repairing broken pottery with gold), this library takes the initial parsing results from Docling and "repairs" complex table structures and text with garbled characters using pdfplumber's precise geometric layout analysis.

## Features

- **Table Parsing:** Improves Docling's table extraction by using pdfplumber to detect omitted geometric lines and infer table edges.
- **Text Correction:** Optionally corrects garbled text using fine-grained character bounding boxes.
- **Seamless Integration with Docling:** Acts as a post-processor for Docling. It takes a `ConversionResult` from Docling, enhances the tables and text in place, and returns the updated document model.

## Installation

The project requires **Python 3.10+**.

You can install it using `pip` or your favorite package manager:

```bash
pip install pdf-kintsugi
```

## Quick Start

`pdf-kintsugi` works alongside `docling`. Here is a basic example of how to use `PDFKintsugi`:

```python
from docling.document_converter import DocumentConverter
from pdf_kintsugi import PDFKintsugi

pdf_path = "path/to/your/document.pdf"

# 1. Parse the document using Docling first
converter = DocumentConverter()
docling_result = converter.convert(pdf_path)

# 2. Initialize PDFKintsugi with the source PDF and the Docling result
kintsugi_parser = PDFKintsugi(
    source=pdf_path,
    docling_result=docling_result,
    tolerance=3.0,          # Adjust merging tolerance for table lines
    replace_text=False,     # Set to True to enable text/character correction
    replace_table=True      # Set to True to enable table structure repair
)

# 3. Get the parsing result
kintsugi_result = kintsugi_parser.parse()

# Now you can use kintsugi_result just like a regular Docling document
print(kintsugi_result.document.export_to_markdown())
```

## Configuration

The `PDFKintsugi` class accepts several parameters to tune the extraction:

- `source` (`str`): The file path to the source PDF document.
- `docling_result` (`ConversionResult`): The parsed document object returned by Docling.
- `tolerance` (`float`, default `3.0`): The line-merging tolerance. A smaller value (e.g., `1.5`) helps prevent adjacent tables from being incorrectly merged, while a larger value (e.g., `5.0`) can help stitch together fragmented tables.
- `replace_text` (`bool`, default `False`): If `True`, utilizes `pdfplumber` to extract characters and correct garbled text.
- `replace_table` (`bool`, default `True`): If `True`, rebuilds and overrides the Docling table representations using geometric line intersections and edge inference.

## Contributing

Contributions are welcome! This project uses `uv` for dependency management.

1. Clone the repository.
2. Setup the environment: `uv sync`
3. Run tests before submitting a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
