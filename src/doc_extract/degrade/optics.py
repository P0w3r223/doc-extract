"""What a scanner does to a page, as pure functions over one image.

Separated from `page.py` for the reason every module here separates transformation from I/O: these
are total functions from an image and a seed to an image, so a test can assert what each one does
without a PDF anywhere near it.

**Every step is seeded, and the seed comes from the document.** A corpus whose grain was drawn from
the ambient random state would have a different hash on every build, and the manifest that attests
to it would be worthless — the same argument `synth/corpus.py` makes for the invoices themselves.

**The noise is uniform rather than Gaussian, and that is a decision about speed, not physics.** An
A4 page at 200 dpi is 3.9 million pixels; drawing that many Gaussian samples in Python takes
longer than rendering the document did. `Random.randbytes` fills the whole plane in one call, and
blending it in at a low weight is visually a sensor's grain. Nothing downstream measures the
distribution of the noise — what is measured is whether a reader can still read the page.
"""

from __future__ import annotations

import io
import random

from PIL import Image, ImageFilter

#: The mode every step works in. A scan is grey: colour would triple the bytes and the corpus prints
#: nothing that carries meaning in hue.
MODE = "L"

#: What the paper is, where a rotation exposes it. White rather than transparent, because the page
#: is opaque and a scanner's lid is not a matte.
PAPER = 255


def skew(image: Image.Image, degrees: float) -> Image.Image:
    """The page rotated on the platen, keeping its size — the corners are cropped, as they are."""
    if degrees == 0:
        return image
    return image.rotate(degrees, resample=Image.Resampling.BICUBIC, fillcolor=PAPER)


def soften(image: Image.Image, radius: float) -> Image.Image:
    """The optics: a glyph edge is never a step function on a scan."""
    if radius <= 0:
        return image
    return image.filter(ImageFilter.GaussianBlur(radius))


def grain(image: Image.Image, rng: random.Random, amount: float) -> Image.Image:
    """Sensor noise, blended in at `amount`. Deterministic in `rng` and in nothing else."""
    if amount <= 0:
        return image
    noise = Image.frombytes(MODE, image.size, rng.randbytes(image.width * image.height))
    return Image.blend(image, noise, amount)


def requantise(image: Image.Image, quality: int) -> bytes:
    """The JPEG round trip, returned as the bytes that go into the page.

    Returned as bytes rather than as an image on purpose: the artefacts are the encoder's, and
    decoding them back into an array only to have the PDF re-encode would apply the damage twice
    and measure a generation loss nobody asked for.
    """
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=False)
    return buffer.getvalue()
