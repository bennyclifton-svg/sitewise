from tender.services.census import census_page


def test_finds_currency_tokens() -> None:
    text = "Total price for demolition services listed above is $46,100 (incl GST)."
    toks = census_page(text, page_no=2)
    assert [t.cents for t in toks] == [4610000]


def test_ignores_abn_phone_and_bare_numbers() -> None:
    text = "ABN: 96150010021 Ph: 0409 142 319 built in 2026 for 331.000 m2"
    assert census_page(text, page_no=1) == []


def test_flags_malformed_grouping() -> None:
    toks = census_page("Internal balustrade and handrail - $9,5556.80", page_no=3)
    assert toks[0].suspect_format is True
    assert toks[0].cents == 955680
