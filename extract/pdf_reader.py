import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from utils.text_utils import clean_text


def read_pdf_pages(path):
    pages_data = []

    print(f"\n📄 Opening PDF: {path}")

    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f"📄 Total pages: {total_pages}")

        for i, page in enumerate(pdf.pages, start=1):
            print(f"📘 Reading page {i}/{total_pages}", end="\r")

            page_parts = []

            text = page.extract_text() or ""
            if text.strip():
                page_parts.append(text)

            tables = page.extract_tables()
            for table_idx, table in enumerate(tables, start=1):
                if not table:
                    continue

                page_parts.append(f"\n[TABLE {table_idx} - PAGE {i}]")
                for row in table:
                    row = [str(cell).strip() for cell in row if cell is not None and str(cell).strip()]
                    if row:
                        page_parts.append("TABLE_ROW: " + " | ".join(row))

            page_text = clean_text("\n".join(page_parts))

            pages_data.append({
                "page": i,
                "text": page_text,
                "source": path
            })

    total_text_len = sum(len(p["text"]) for p in pages_data)

    if total_text_len < 50:
        print("\n⚠️ Using OCR fallback...")
        images = convert_from_path(path)
        pages_data = []

        for i, img in enumerate(images, start=1):
            print(f"🧠 OCR page {i}/{len(images)}", end="\r")
            ocr_text = clean_text(pytesseract.image_to_string(img))
            pages_data.append({
                "page": i,
                "text": ocr_text,
                "source": path
            })

    print()
    return pages_data