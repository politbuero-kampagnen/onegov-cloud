from onegov.swissvotes.utils import search_term_expression


def test_votes_term_expression(swissvotes_app):
    assert search_term_expression(None) == ''
    assert search_term_expression('') == ''
    assert search_term_expression('a,1.$b !c*d*') == 'a,1.b <-> cd:*'
