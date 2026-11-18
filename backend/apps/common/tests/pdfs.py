"""Hand-built PDFs for the upload tests (valid xref streams, so qpdf parses them without repair)."""
import binascii
import io
import zlib

import pikepdf


def simple_pdf(text=b"Hello"):
    pdf = pikepdf.new()
    pdf.add_blank_page(page_size=(100, 100))
    page = pdf.pages[0]
    page.Contents = pdf.make_stream(b"BT /F1 12 Tf (" + text + b") Tj ET")
    out = io.BytesIO()
    pdf.save(out, compress_streams=True)
    return out.getvalue()


def objstm_action_pdf(filters, action=b"<< /S /JavaScript /JS (app.alert(1)) >>"):
    """Catalog /OpenAction -> object 6, which lives in an object stream encoded with `filters`
    (list of filter names, applied as the PDF /Filter array: first entry is decoded first)."""
    body = action
    stm_data = b"6 0 " + body
    first = len(b"6 0 ")
    encoded = stm_data
    for name in reversed(filters):  # encode innermost-last so that decoding in order restores it
        encoded = {"ASCIIHexDecode": lambda d: binascii.hexlify(d) + b">",
                   "FlateDecode": zlib.compress}[name](encoded)
    filt = b"/" + filters[0].encode() if len(filters) == 1 else b"[" + b" ".join(b"/" + f.encode() for f in filters) + b"]"

    objs = {
        1: b"<< /Type /Catalog /Pages 2 0 R /OpenAction 6 0 R >>",
        2: b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        3: b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 10 10] >>",
        4: b"<< /Type /ObjStm /N 1 /First %d /Filter %s /Length %d >>\nstream\n" % (first, filt, len(encoded))
           + encoded + b"\nendstream",
    }
    out = bytearray(b"%PDF-1.7\n")
    offsets = {}
    for num, content in objs.items():
        offsets[num] = len(out)
        out += b"%d 0 obj\n" % num + content + b"\nendobj\n"
    xref_off = len(out)
    rows = [b"\x00\x00\x00\xff\xff"]
    for num in (1, 2, 3, 4):
        rows.append(b"\x01" + offsets[num].to_bytes(2, "big") + b"\x00\x00")
    rows.append(b"\x01" + xref_off.to_bytes(2, "big") + b"\x00\x00")  # 5: the xref stream itself
    rows.append(b"\x02" + (4).to_bytes(2, "big") + b"\x00\x00")       # 6: in object stream 4, index 0
    data = b"".join(rows)
    out += (b"5 0 obj\n<< /Type /XRef /Size 7 /W [1 2 2] /Root 1 0 R /Length %d >>\nstream\n" % len(data)
            + data + b"\nendstream\nendobj\nstartxref\n%d\n%%%%EOF\n" % xref_off)
    return bytes(out)
