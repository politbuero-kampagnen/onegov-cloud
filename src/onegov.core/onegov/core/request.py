from cached_property import cached_property
from more.webassets.core import IncludeRequest
from onegov.core import utils


class CoreRequest(IncludeRequest):
    """ Extends the default Morepath request with virtual host support and
    other useful methods.

    Virtual hosting might be supported by Morepath directly in the future:
    https://github.com/morepath/morepath/issues/185

    """

    def link_prefix(self):
        """ Override the `link_prefix` with the application base path provided
        by onegov.server, because the default link_prefix contains the
        hostname, which is not useful in our case - we'll add the hostname
        ourselves later.

        """
        return getattr(self.app, 'application_base_path', '')

    @cached_property
    def x_vhm_host(self):
        """ Return the X_VHM_HOST variable or an empty string.

        X_VHM_HOST acts like a prefix to all links generated by Morepath.
        If this variable is not empty, it will be added in front of all
        generated urls.
        """
        return self.headers.get('X_VHM_HOST', '').rstrip('/')

    @cached_property
    def x_vhm_root(self):
        """ Return the X_VHM_ROOT variable or an empty string.

        X_VHM_ROOT is a bit more tricky than X_VHM_HOST. It tells Morepath
        where the root of the application is situated. This means that the
        value of X_VHM_ROOT must be an existing path inside of Morepath.

        We can understand this best with an example. Let's say you have a
        Morepath application that serves a blog under /blog. You now want to
        serve the blog under a separate domain, say blog.example.org.

        If we just served Morepath under blog.example.org, we'd get urls like
        this one::

            blog.example.org/blog/posts/2014-11-17-16:00

        In effect, this subdomain would be no different from example.org
        (without the blog subdomain). However, we want the root of the host to
        point to /blog.

        To do this we set X_VHM_ROOT to /blog. Morepath will then automatically
        return urls like this::

            blog.example.org/posts/2014-11-17-16:00

        """
        return self.headers.get('X_VHM_ROOT', '').rstrip('/')

    def transform(self, url):
        """ Applies X_VHM_HOST and X_VHM_ROOT to the given url (which is
        expected to not contain a host yet!). """
        if self.x_vhm_root:
            url = '/' + utils.lchop(url, self.x_vhm_root).lstrip('/')

        if self.x_vhm_host:
            url = self.x_vhm_host + url

        return url

    def link(self, *args, **kwargs):
        """ Extends the default link generating function of Morepath. """
        return self.transform(
            super(CoreRequest, self).link(*args, **kwargs))

    def filestorage_link(self, path):
        """ Takes the given filestorage path and returns an url if the path
        exists. The url might point to the local server or it might point to
        somehwere else on the web.

        """

        app = self.app

        if not app.filestorage.exists(path):
            return None

        url = app.filestorage.getpathurl(path, allow_none=True)

        if url:
            return url
        else:
            return self.link(app.modules.filestorage.FilestorageFile(path))
