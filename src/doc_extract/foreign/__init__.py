"""M7 — the same invoices, printed by somebody else.

The synthetic corpus varies what an invoice *means*: grosz rounding, corrections, reverse charge,
two pages. It does not vary how the page *says* it. Three layouts share one vocabulary, one number
format and one date format, all of them `synth/render.py`'s — so a reader fitted to that page has
been fitted to the whole corpus, and nothing in the project could say by how much.

This package prints the identical gold on a page that vocabulary has never been seen on. Different
Polish labels for every field, different column orders, different number and date formats, and
block orders that put the totals before the rows. **The gold is untouched**, exactly as M6's
attacked corpus leaves it untouched, so the scorer, the detector and the gate all run over it with
no special casing and a result is one more reading of the same prediction file.

**It is a paired comparison, and that is what it buys.** Document `clean-0000` here is document
`clean-0000` there: same seed, same seller, same rows, same total. A difference between the two runs
is therefore the *page*, because nothing else moved. A held-out set of genuinely foreign invoices
would vary the data too, and would not be able to say which half of the drop was which.

**It is not a real held-out set and this package does not claim to be one.** It holds the semantics
fixed on purpose, so it measures one thing: how much of a result was presentation. Real invoices
carry skew, stamps, scans and layouts nobody anticipated, and none of that is here. What this can
answer is the question the project can otherwise only assert — whether `eval/pattern.py`'s 86.3 %
was reading or was template knowledge, and whether a prompt forbidden to know the corpus's labels
actually transfers when the labels change.
"""
