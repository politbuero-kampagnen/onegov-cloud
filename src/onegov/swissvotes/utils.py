
def search_term_expression(term):
    """ Returns the given search term transformed to use within Postgres
    ``to_tsquery`` function.

    Removes all unwanted characters, replaces prefix matching, joins
    word together using FOLLOWED BY.
    """

    def cleanup(text):
        result = ''.join((c for c in text if c.isalnum() or c in ',.'))
        return f'{result}:*' if text.endswith('*') else result

    parts = [cleanup(part) for part in (term or '').strip().split()]
    return ' <-> '.join([part for part in parts if part])
