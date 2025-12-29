import pypdfium2 as pdfium
from PIL import Image

def test_render():
    # Load test pdf
    pdf = pdfium.PdfDocument("test_statement.pdf")
    n_pages = len(pdf)
    print(f"Pages: {n_pages}")

    for i in range(n_pages):
        page = pdf[i]
        bitmap = page.render(scale=2) # 2x scale for better OCR
        pil_image = bitmap.to_pil()
        print(f"Page {i} rendered to {pil_image}")
        pil_image.save(f"page_{i}.png")

if __name__ == "__main__":
    test_render()
