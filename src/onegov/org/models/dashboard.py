class Dashboard(object):

    def __init__(self, request):
        self.request = request

    @property
    def is_available(self):
        return self.request.app.config.boardlets_registry and True or False

    def boardlets(self):
        import pdb; pdb.set_trace()
