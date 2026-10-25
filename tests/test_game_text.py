from app.core.game_text import clean_game_json, clean_text

RETRIBUTION = (
    "Deal 520 (+80*Hero Level) <font color=\"ffe63c\">True Damage</font> to the target Creep or Minion.\n"
    "<font color=\"62f8fe\">Blessing:</font> Accumulate 5 Creep kills, hero kills, or assists to upgrade the spell "
    "according to the Jungling Boots' Blessing, and <Num9> kills or assists to gain <Num10> Physical Attack and "
    "Magic Power and <Num11> Max HP."
)


def test_cuts_the_clause_whose_numbers_are_missing():
    assert clean_text(RETRIBUTION) == (
        "Deal 520 (+80*Hero Level) <font color=\"ffe63c\">True Damage</font> to the target Creep or Minion.\n"
        "<font color=\"62f8fe\">Blessing:</font> Accumulate 5 Creep kills, hero kills, or assists to upgrade the spell "
        "according to the Jungling Boots' Blessing."
    )


def test_drops_a_sentence_with_no_comma_and_keeps_decimals():
    text = "Gain 0.5% Spell Vamp. Lasts <Num2>s after a kill. Stacks 8 times."
    assert clean_text(text) == "Gain 0.5% Spell Vamp. Stacks 8 times."


def test_removes_live_counters():
    text = "Unlock Conceal! (Current: <font color=\"ffe63c\"> <#bv 25></font>) Active: camouflage."
    assert clean_text(text) == "Unlock Conceal! Active: camouflage."
    assert clean_text("Gold: <#bv 3>") == "Gold: "


def test_leaves_templates_and_plain_text_alone():
    data = {"skilldesc": "Gain <Num1> Defense.", "skilldesc_text": "Gain <Num1> Defense.", "n": 5, "list": ["plain"]}
    assert clean_game_json(data) == {"skilldesc": "", "skilldesc_text": "Gain <Num1> Defense.", "n": 5, "list": ["plain"]}
