from twitchdl.utils import titlify, slugify


def test_titlify():
    assert titlify("Foo Bar Baz.") == "Foo Bar Baz."
    assert titlify("Foo (Bar) [Baz]") == "Foo (Bar) [Baz]"
    assert titlify("Foo@{} Bar Baz!\"#$%&/=?*+'🔪") == "Foo Bar Baz"


def test_slugify():
    assert slugify("Foo Bar Baz") == "foo_bar_baz"
    assert slugify("  Foo   Bar   Baz  ") == "foo_bar_baz"
    assert slugify("Foo@{}[] Bar Baz!\"#$%&/()=?*+'🔪") == "foo_bar_baz"
