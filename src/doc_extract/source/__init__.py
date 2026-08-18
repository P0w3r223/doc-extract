"""The untrusted-data layer: a PDF read back as text, with every character traceable to the page.

Three things happen here and nothing else does. The PDF is read into **words with geometry**; the
words are grouped into lines and cells by that geometry rather than by a flat text dump; and the
result is wrapped in a delimited envelope that says, to whatever reads it next, *this is data*.

No model, no network, no interpretation of what any value means. `extract` decides what the numbers
are; this package only decides what is written where.
"""
