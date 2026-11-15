import pytest

from photos import credit_line, is_free_license


@pytest.mark.parametrize("lic,ok", [("CC0", True), ("CC BY 2.0", True), ("CC BY-SA 4.0", True), ("Public domain", True),
                                    ("CC BY-NC 2.0", False), ("CC BY-ND 4.0", False), ("", False)])
def test_license_filter(lic, ok):
    assert is_free_license(lic) is ok


def test_credit_line_strips_html():
    assert credit_line({"author": '<a href="x">JohnLim99</a>', "license": "CC BY-SA 4.0"}) == "Photo: JohnLim99 · CC BY-SA 4.0 · Wikimedia Commons"


def test_credit_line_unknown_and_long_author():
    assert credit_line({"author": "", "license": "CC0"}) == "Photo: unknown · CC0 · Wikimedia Commons"
    assert len(credit_line({"author": "x" * 200, "license": "CC0"})) == len("Photo:  · CC0 · Wikimedia Commons") + 80


def test_shrink_jpeg_meets_size_and_width():
    import io

    import numpy as np
    from PIL import Image

    from photos import shrink_jpeg
    noise = (np.random.default_rng(0).random((900, 1400, 3)) * 255).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(noise).save(buf, "JPEG", quality=95)
    assert len(buf.getvalue()) > 250_000
    out = shrink_jpeg(buf.getvalue(), max_bytes=250_000, max_width=960)
    img = Image.open(io.BytesIO(out))
    assert len(out) <= 250_000 and img.width <= 960 and img.format == "JPEG"
