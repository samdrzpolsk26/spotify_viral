from music_intel.etl.transform import make_artist_id, split_artist_credit


def test_split_artist_credit_separates_main_and_featured_artists() -> None:
    main, featured = split_artist_credit("Luna Vale & Rio Nexo feat. Kai North, Mika Sol")

    assert main == ["Luna Vale", "Rio Nexo"]
    assert featured == ["Kai North", "Mika Sol"]


def test_make_artist_id_is_stable_slug() -> None:
    assert make_artist_id("Kai North") == "artist_kai_north"
