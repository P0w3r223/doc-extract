"""The synthetic corpus: KSeF FA(3) documents whose ground truth is the document itself.

Generation runs offline and needs no model. `build` produces the invoice, `fa3_xml` writes it as a
schema-valid FA(3) document and reads it back as gold, `render` prints it in one of three layouts,
and `corpus` assembles the whole thing from a single seed.
"""
