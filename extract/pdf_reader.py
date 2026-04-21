import unicodedata
import pdfplumber
import pytesseract
from pdf2image import convert_from_path
from utils.text_utils import clean_text

MIN_TEXT_THRESHOLD_PER_PAGE = 80


def _looks_garbled(text: str) -> bool:
    if not text:
        return True
    weird_char_count = sum(1 for ch in text if ord(ch) > 127)
    replacement_count = text.count("�")
    return replacement_count > 2 or weird_char_count > max(20, int(len(text) * 0.15))


def read_pdf_pages(path: str) -> list[dict]:
    pages_data = []
    print(f"\n📄 Opening PDF: {path}")

    with pdfplumber.open(path) as pdf:
        total_pages = len(pdf.pages)
        print(f"📄 Total pages: {total_pages}")

        page_images = None
        for i, page in enumerate(pdf.pages, start=1):
            print(f"📘 Reading page {i}/{total_pages}", end="\r")
            try:
                table_bboxes = [tbl.bbox for tbl in page.find_tables()]
            except Exception:
                table_bboxes = []

            if table_bboxes:
                prose_page = page
                for bbox in table_bboxes:
                    try:
                        prose_page = prose_page.filter(
                            lambda obj, b=bbox: not (b[0] <= obj["x0"] <= b[2] and b[1] <= obj["top"] <= b[3])
                        )
                    except Exception:
                        pass
                raw_text = prose_page.extract_text() or ""
            else:
                raw_text = page.extract_text() or ""

            page_text = clean_text(raw_text)
            weak_native_text = len(page_text) < MIN_TEXT_THRESHOLD_PER_PAGE or _looks_garbled(page_text)

            if weak_native_text:
                if page_images is None:
                    print("\n⚠️  Preparing page images for selective OCR...")
                    page_images = convert_from_path(path)
                print(f"🧠 OCR page {i}/{total_pages}", end="\r")
                ocr_text = clean_text(pytesseract.image_to_string(page_images[i - 1]))
                if len(ocr_text) > len(page_text) or (len(ocr_text) >= 40 and _looks_garbled(page_text)):
                    page_text = ocr_text

            pages_data.append({"page": i, "text": page_text, "source": path})

    print()
    return pages_data
