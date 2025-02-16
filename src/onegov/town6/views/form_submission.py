from onegov.core.security import Public, Private
from onegov.org.views.form_submission import handle_pending_submission
from onegov.form import (
    PendingFormSubmission,
    CompleteFormSubmission
)
from onegov.town6 import TownApp
from onegov.town6.layout import FormSubmissionLayout


@TownApp.html(model=PendingFormSubmission, template='submission.pt',
              permission=Public, request_method='GET')
@TownApp.html(model=PendingFormSubmission, template='submission.pt',
              permission=Public, request_method='POST')
@TownApp.html(model=CompleteFormSubmission, template='submission.pt',
              permission=Private, request_method='GET')
@TownApp.html(model=CompleteFormSubmission, template='submission.pt',
              permission=Private, request_method='POST')
def town_handle_pending_submission(self, request):
    if 'title' in request.GET:
        title = request.GET['title']
    else:
        title = self.form.title
    return handle_pending_submission(
        self, request, FormSubmissionLayout(self, request, title))
