import os.path

from csscompressor import compress
from scss.compiler import Compiler


class BaseTheme(object):
    """ Base class for Zurb Foundation based themes. Use this class to
    create a theme that customizes Zurb Foundation somehow.

    If you don't want to customize it at all, use :class:`Theme`.

    To customize start like this::

        from onegov.foundation import BaseTheme

        class MyTheme(BaseTheme):
            name = 'my-theme'
            version = '1.0'

    You can then add paths with your own scss files, as well as imports that
    should be added *before* the foundation theme, and imports that should
    be added *after* the foundation theme.

    Finally, options passed to the :meth:`compile` function take this form::

        options = {
            'rowWidth': '1000px',
            'columnGutter': '30px'
        }

    Those options result in variables added at the very top of the sass source
    before it is compiled::

        @import 'foundation/functions';

        $rowWidth: 1000px;
        $columnGutter: 30px;

    If your variables rely on a certain order you need to pass an ordered dict.

    """

    def __init__(self, compress=True):
        """ Initializes the theme.

        :compress:
            If true, which is the default, the css is compressed before it is
            returned.

        """
        self.compress = compress

    @property
    def pre_imports(self):
        """ Imports added before the foundation import. The imports must be
        found in one of the paths (see :attr:`extra_search_paths`).

        The form of a single import is 'example' (which would search for
        files named 'example.scss')

        """
        return []

    @property
    def imports(self):
        """ All imports, including the foundation ones. Override with care. """
        return self.pre_imports\
            + ['normalize', 'foundation']\
            + self.post_imports

    @property
    def post_imports(self):
        """
        Imports added after the foundation import. The imports must be found
        in one of the paths (see :attr:`extra_search_paths`).

        The form of a single import is 'example' (which would search for
        files named 'example.scss')

        """
        return []

    @property
    def extra_search_paths(self):
        """ A list of absolute search paths added before the actual foundation
        search path.

        """
        return []

    @property
    def foundation_path(self):
        """ The search path for the foundation files included in this module.

        """
        return os.path.join(os.path.dirname(__file__), 'foundation')

    def compile(self, options={}):
        """ Compiles the theme with the given options. """

        if options:
            prefix = "@import 'foundation/functions';"
            prefix = prefix + '\n'.join(
                "${}: {};".format(k, v) for k, v in options.items()
            )
        else:
            prefix = ""

        paths = self.extra_search_paths
        paths.append(self.foundation_path)

        compiler = Compiler(search_path=paths)
        css = compiler.compile_string(
            prefix + '\n'.join("@import '{}';".format(i) for i in self.imports)
        )

        if self.compress:
            return compress(css)
        else:
            return css


class Theme(BaseTheme):
    name = 'onegov.foundation'
    version = '1.0'
