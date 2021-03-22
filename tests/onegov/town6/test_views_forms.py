import textwrap
from datetime import date

import transaction
from freezegun import freeze_time
from webtest import Upload

from onegov.form import FormCollection
from onegov.ticket import TicketCollection
from tests.shared.utils import create_image


def test_view_form_alert(client):
    login = client.get('/auth/login').form.submit()
    assert 'Das Formular enthält Fehler' in login


def test_submit_form(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Profile', definition=textwrap.dedent("""
        # Your Details
        First name * = ___
        Last name * = ___
        E-Mail * = @@@
    """), type='custom')

    transaction.commit()

    form_page = client.get('/forms').click('Profile')
    assert 'Your Details' in form_page
    assert 'First name' in form_page
    assert 'Last name' in form_page
    assert 'E-Mail' in form_page

    assert 'form/' in form_page.request.url
    form_page = form_page.form.submit().follow()

    assert 'form/' not in form_page.request.url
    assert 'form-preview' in form_page.request.url
    assert len(form_page.pyquery('small.error')) == 3

    form_page.form['your_details_first_name'] = 'Kung'
    form_page = form_page.form.submit()

    assert len(form_page.pyquery('small.error')) == 2

    form_page.form['your_details_last_name'] = 'Fury'
    form_page.form['your_details_e_mail'] = 'kung.fury@example.org'
    form_page = form_page.form.submit()

    assert len(form_page.pyquery('small.error')) == 0
    ticket_page = form_page.form.submit().follow()

    # make sure a ticket has been created
    assert 'FRM-' in ticket_page
    assert 'ticket-state-open' in ticket_page

    tickets = TicketCollection(client.app.session()).by_handler_code('FRM')
    assert len(tickets) == 1

    assert tickets[0].title == 'Kung, Fury, kung.fury@example.org'
    assert tickets[0].group == 'Profile'

    # the user should have gotten an e-mail with the entered data
    message = client.app.smtp.outbox[-1]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('iso-8859-1')

    assert 'Fury' in message

    # unless he opts out of it
    form_page = client.get('/forms').click('Profile')
    form_page = form_page.form.submit().follow()
    form_page.form['your_details_first_name'] = 'Kung'
    form_page.form['your_details_last_name'] = 'Fury'
    form_page.form['your_details_e_mail'] = 'kung.fury@example.org'
    form_page = form_page.form.submit()

    form_page.form.get('send_by_email', index=0).value = False
    ticket_page = form_page.form.submit().follow()

    message = client.app.smtp.outbox[-1]
    message = message.get_payload(0).get_payload(decode=True)
    message = message.decode('iso-8859-1')

    assert 'Fury' not in message


def test_pending_submission_error_file_upload(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Statistics', definition=textwrap.dedent("""
        Name * = ___
        Datei * = *.txt|*.csv
    """), type='custom')
    transaction.commit()

    form_page = client.get('/forms').click('Statistics')
    form_page.form['datei'] = Upload('test.jpg', create_image().read())

    form_page = form_page.form.submit().follow()
    assert 'form-preview' in form_page.request.url
    assert len(form_page.pyquery('small.error')) == 2


def test_pending_submission_successful_file_upload(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Statistics', definition=textwrap.dedent("""
        Name * = ___
        Datei * = *.txt|*.csv
    """), type='custom')
    transaction.commit()

    form_page = client.get('/forms').click('Statistics')
    form_page.form['datei'] = Upload('README.txt', b'1;2;3')
    form_page = form_page.form.submit().follow()

    assert "README.txt" in form_page.text
    assert "Datei ersetzen" in form_page.text
    assert "Datei löschen" in form_page.text
    assert "Datei behalten" in form_page.text

    # unfortunately we can't test more here, as webtest doesn't support
    # multiple differing fields of the same name...


def test_add_custom_form(client):
    client.login_editor()

    # this error is not strictly line based, so there's a general error
    form_page = client.get('/forms/new')
    form_page.form['title'] = "My Form"
    form_page.form['lead'] = "This is a form"
    form_page.form['text'] = "There are many like it, but this one's mine"
    form_page.form['definition'] = "abc ="
    form_page = form_page.form.submit()

    assert "Das Formular ist nicht gültig." in form_page

    # this error is line based
    form_page = client.get('/forms/new')
    form_page.form['title'] = "My Form"
    form_page.form['lead'] = "This is a form"
    form_page.form['text'] = "There are many like it, but this one's mine"
    form_page.form['definition'] = "xxx = !!!"
    form_page = form_page.form.submit()

    assert "Der Syntax in der 1. Zeile ist ungültig." in form_page
    assert 'data-highlight-line="1"' in form_page

    form_page.form['definition'] = "Name * = ___\nE-Mail * = @@@"
    form_page = form_page.form.submit().follow()

    form_page.form['name'] = 'My name'
    form_page.form['e_mail'] = 'my@name.com'
    form_page = form_page.form.submit().follow()

    form_page = client.get('/form/my-form/edit')
    form_page.form['definition'] = "Nom * = ___\nMail * = @@@"
    form_page = form_page.form.submit().follow()

    form_page.form['nom'] = 'My name'
    form_page.form['mail'] = 'my@name.com'
    form_page.form.submit().follow()


def test_add_duplicate_form(client):
    client.login_editor()

    form_page = client.get('/forms/new')
    form_page.form['title'] = "My Form"
    form_page.form['lead'] = "This is a form"
    form_page.form['text'] = "There are many like it, but this one's mine"
    form_page.form['definition'] = "email *= @@@"
    form_page = form_page.form.submit().follow()

    assert "Ein neues Formular wurd hinzugefügt" in form_page

    form_page = client.get('/forms/new')
    form_page.form['title'] = "My Form"
    form_page.form['lead'] = "This is a form"
    form_page.form['text'] = "There are many like it, but this one's mine"
    form_page.form['definition'] = "email *= @@@"
    form_page = form_page.form.submit()

    assert "Ein Formular mit diesem Namen existiert bereits" in form_page


def test_delete_custom_form(client):
    client.login_editor()

    form_page = client.get('/forms/new')
    form_page.form['title'] = "My Form"
    form_page.form['definition'] = "e-mail * = @@@"
    form_page = form_page.form.submit().follow()

    client.delete(
        form_page.pyquery('a.delete-link')[0].attrib['ic-delete-from'])


def test_show_uploaded_file(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add(
        'Text', definition="File * = *.txt\nE-Mail * = @@@", type='custom')
    transaction.commit()

    client.login_editor()

    form_page = client.get('/form/text')
    form_page.form['e_mail'] = 'info@example.org'
    form_page.form['file'] = Upload('test.txt', b'foobar')
    form_page = form_page.form.submit().follow()  # preview
    form_page = form_page.form.submit().follow()  # finalize

    ticket_page = client.get(
        form_page.pyquery('.ticket-number a').attr('href'))

    assert 'test.txt' in ticket_page.text
    file_response = ticket_page.click('test.txt', index=0)

    assert file_response.content_type == 'text/plain'
    assert file_response.text == 'foobar'

    assert file_response.cache_control.private
    assert file_response.cache_control.no_cache
    assert not file_response.cache_control.public

    assert client.spawn().get(file_response.request.url, status=404)


def test_manual_form_payment(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Govikon Poster', definition=textwrap.dedent("""
        E-Mail *= @@@

        Posters *=
            [ ] Local Businesses (0 CHF)
            [ ] Executive Committee (10 CHF)
            [ ] Town Square (20 CHF)

        Delivery *=
            ( ) Pickup (0 CHF)
            ( ) Delivery (5 CHF)
    """), type='custom')

    transaction.commit()

    page = client.get('/form/govikon-poster')
    assert '10.00 CHF' in page
    assert '20.00 CHF' in page
    assert '5.00 CHF' in page

    page.form['e_mail'] = 'info@example.org'
    page.select_checkbox('posters', "Executive Committee")
    page.select_checkbox('posters', "Town Square")
    page.form['delivery'] = 'Delivery'

    page = page.form.submit().follow()
    assert "Totalbetrag" in page
    assert "35.00 CHF" in page

    page = page.form.submit().follow()
    assert "Referenz Anfrage" in page

    client.login_editor()
    page = client.get('/tickets/ALL/open').click("Annehmen").follow()

    assert page.pyquery('.payment-state').text() == "Offen"

    client.post(page.pyquery('.mark-as-paid').attr('ic-post-to'))
    page = client.get(page.request.url)

    assert page.pyquery('.payment-state').text() == "Bezahlt"

    client.post(page.pyquery('.mark-as-unpaid').attr('ic-post-to'))
    page = client.get(page.request.url)

    assert page.pyquery('.payment-state').text() == "Offen"

    payments = client.get('/payments')
    assert "FRM-" in payments
    assert "Manuell" in payments
    assert "info@example.org" in payments
    assert "35.00" in payments
    assert "Offen" in payments


def test_dependent_number_form(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Profile', definition=textwrap.dedent("""
        E-Mail *= @@@
        Country =
            ( ) Switzerland
                Email *= @@@
            (x) Other
    """), type='custom')

    transaction.commit()

    page = client.get('/form/profile')
    page.form['e_mail'] = 'info@example.org'
    page = page.form.submit().follow()

    assert "Bitte überprüfen Sie Ihre Angaben" in page


def test_registration_form_hints(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Meetup', "E-Mail *= @@@", 'custom')
    transaction.commit()

    client.login_editor()

    page = client.get('/form/meetup')
    page = page.click("Hinzufügen")

    page.form['start'] = '2018-01-01'
    page.form['end'] = '2018-01-31'
    page.form['limit_attendees'] = 'yes'
    page.form['limit'] = 2
    page.form['waitinglist'] = 'yes'
    page.form['stop'] = False
    page = page.form.submit().follow()

    assert "Der Anmeldezeitraum wurde erfolgreich hinzugefügt" in page

    # the time here is in UTC, offset is +1 hour
    with freeze_time('2017-12-31 22:59:59'):
        page = client.get('/form/meetup')
        assert "Die Anmeldung beginnt am Montag, 01. Januar 2018" in page

    with freeze_time('2017-12-31 23:00:00'):
        page = client.get('/form/meetup')
        assert "Die Anmeldung endet am Mittwoch, 31. Januar 2018" in page

    with freeze_time('2018-01-31 22:59:59'):
        page = client.get('/form/meetup')
        assert "Die Anmeldung endet am Mittwoch, 31. Januar 2018" in page

    with freeze_time('2018-01-31 23:00:00'):
        page = client.get('/form/meetup')
        assert "Die Anmeldung ist nicht mehr möglich" in page

    edit = page.click('01.01.2018 - 31.01.2018').click('Bearbeiten')
    edit.form['stop'] = True
    edit.form.submit()

    with freeze_time('2018-01-01'):
        page = client.get('/form/meetup')
        assert "Zur Zeit keine Anmeldung möglich" in page

        edit.form['stop'] = False
        edit.form.submit()

        page = client.get('/form/meetup')
        assert "Die Anmeldung endet am Mittwoch, 31. Januar 2018" in page
        assert "Die Anmeldung ist auf 2 Teilnehmer begrenzt" in page

        edit.form['waitinglist'] = 'no'
        edit.form.submit()

        page = client.get('/form/meetup')
        assert "Es sind noch 2 Plätze verfügbar" in page

        edit.form['limit'] = 1
        edit.form.submit()

        page = client.get('/form/meetup')
        assert "Es ist noch ein Platz verfügbar" in page

        page.form['e_mail'] = 'info@example.org'
        page.form.submit().follow().form.submit()

        page = client.get('/form/meetup')
        assert "Keine Plätze mehr verfügbar" in page


def test_registration_complete_after_deadline(client):
    collection = FormCollection(client.app.session())

    form = collection.definitions.add('Meetup', "E-Mail *= @@@", 'custom')
    form.add_registration_window(
        start=date(2018, 1, 1),
        end=date(2018, 1, 31),
    )

    transaction.commit()

    # the registration is started before the end of the deadline
    with freeze_time('2018-01-31 22:59:59'):
        page = client.get('/form/meetup')
        page.form['e_mail'] = 'info@example.org'
        page = page.form.submit().follow()

    # but it is completed after the deadline (no longer possible)
    with freeze_time('2018-01-31 23:00:00'):
        page = page.form.submit().follow()
        assert "Anmeldungen sind nicht mehr möglich" in page
        assert TicketCollection(client.app.session()).query().count() == 0


def test_registration_race_condition(client):
    collection = FormCollection(client.app.session())

    form = collection.definitions.add('Meetup', "E-Mail *= @@@", 'custom')
    form.add_registration_window(
        start=date(2018, 1, 1),
        end=date(2018, 1, 31),
        limit=1,
        overflow=False
    )

    transaction.commit()

    foo = client.spawn()
    bar = client.spawn()

    def fill_out_form(client):
        page = client.get('/form/meetup')
        page.form['e_mail'] = 'info@example.org'

        return page.form.submit().follow()

    def complete_form(page):
        return page.form.submit().follow()

    with freeze_time('2018-01-01'):
        foo = fill_out_form(foo)
        bar = fill_out_form(bar)

        assert "Vielen Dank für Ihre Eingabe" in complete_form(foo)
        assert "Anmeldungen sind nicht mehr möglich" in complete_form(bar)


def test_registration_change_limit_after_submissions(client):
    collection = FormCollection(client.app.session())

    form = collection.definitions.add('Meetup', "E-Mail *= @@@", 'custom')
    form.add_registration_window(
        start=date(2018, 1, 1),
        end=date(2018, 1, 31),
        limit=10,
        overflow=False
    )

    transaction.commit()

    client.login_editor()

    with freeze_time('2018-01-01'):
        for i in range(0, 3):
            page = client.get('/form/meetup')
            page.form['e_mail'] = 'info@example.org'
            page.form.submit().follow().form.submit().follow()

    page = client.get('/form/meetup').click('01.01.2018 - 31.01.2018')
    page = page.click('Bearbeiten')

    page.form['limit'] = 1
    assert "nicht tiefer sein als die Summe" in page.form.submit()

    submissions = collection.submissions.query().all()
    submissions[0].claim()
    submissions[1].claim()
    transaction.commit()

    page.form['waitinglist'] = 'yes'
    assert "nicht tiefer sein als die Anzahl" in page.form.submit()

    page.form['waitinglist'] = 'no'
    page.form['limit'] = 2
    assert "nicht tiefer sein als die Summe" in page.form.submit()

    submissions = collection.submissions.query().all()
    submissions[2].disclaim()
    transaction.commit()

    page = page.form.submit().follow()
    assert "Ihre Änderungen wurden gespeichert" in page

    submissions = collection.submissions.query().all()
    submissions[1].disclaim()
    transaction.commit()

    page = page.click('01.01.2018 - 31.01.2018').click('Bearbeiten')
    page.form['limit'] = 1
    page = page.form.submit().follow()

    assert "Ihre Änderungen wurden gespeichert" in page


def test_registration_ticket_workflow(client):
    collection = FormCollection(client.app.session())

    form = collection.definitions.add('Meetup', textwrap.dedent("""
        E-Mail *= @@@
        Name *= ___
    """), 'custom')

    form.add_registration_window(
        start=date(2018, 1, 1),
        end=date(2018, 1, 31),
        limit=10,
        overflow=False
    )

    transaction.commit()

    client.login_editor()

    def register(e_mail, name, include_data_in_email):

        with freeze_time('2018-01-01'):
            page = client.get('/form/meetup')
            page.form['e_mail'] = 'info@example.org'
            page.form['name'] = 'Foobar'
            page = page.form.submit().follow()

            page.form['send_by_email'] = include_data_in_email
            page.form.submit().follow()

        return client.get('/tickets/ALL/open').click("Annehmen").follow()

    page = register('info@example.org', 'Foobar', include_data_in_email=True)

    assert "bestätigen" in page
    assert "ablehnen" in page

    msg = client.app.smtp.sent[-1]
    assert "Ihre Anfrage wurde unter der folgenden Referenz registriert" in msg
    assert "Foobar" in msg

    page = page.click("Anmeldung bestätigen").follow()

    msg = client.app.smtp.sent[-1]
    assert 'Ihre Anmeldung für "Meetup" wurde bestätigt' in msg
    assert "01.01.2018 - 31.01.2018" in msg
    assert "Foobar" in msg

    page = page.click("Anmeldung stornieren").follow()

    msg = client.app.smtp.sent[-1]
    assert 'Ihre Anmeldung für "Meetup" wurde storniert' in msg
    assert "01.01.2018 - 31.01.2018" in msg
    assert "Foobar" in msg

    page = register('info@example.org', 'Foobar', include_data_in_email=False)

    msg = client.app.smtp.sent[-1]
    assert "Ihre Anfrage wurde unter der folgenden Referenz registriert" in msg
    assert "Foobar" not in msg

    page.click("Anmeldung ablehnen")

    msg = client.app.smtp.sent[-1]
    assert 'Ihre Anmeldung für "Meetup" wurde abgelehnt' in msg
    assert "01.01.2018 - 31.01.2018" in msg
    assert "Foobar" not in msg


def test_registration_not_in_front_of_queue(client):
    collection = FormCollection(client.app.session())

    form = collection.definitions.add('Meetup', "E-Mail *= @@@", 'custom')
    form.add_registration_window(
        start=date(2018, 1, 1),
        end=date(2018, 1, 31),
        limit=10,
        overflow=False
    )

    transaction.commit()

    client.login_editor()

    with freeze_time('2018-01-01'):
        for i in range(0, 2):
            page = client.get('/form/meetup')
            page.form['e_mail'] = 'info@example.org'
            page.form.submit().follow().form.submit().follow()

    page = client.get('/tickets/ALL/open').click("Annehmen", index=1).follow()
    assert "Dies ist nicht die älteste offene Eingabe" in page

    page = client.get('/tickets/ALL/open').click("Annehmen").follow()
    assert "Dies ist nicht die älteste offene Eingabe" not in page


def test_markdown_in_forms(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Content', definition=textwrap.dedent("""
        E-Mail *= @@@
        Content = <markdown>
    """), type='custom')

    transaction.commit()

    page = client.get('/forms').click('Content')
    page.form['e_mail'] = 'info@example.org'
    page.form['content'] = '* foo\n* bar'
    page = page.form.submit().follow()

    assert '<li>foo</li>' in page
    assert '<li>bar</li>' in page


def test_exploit_markdown_in_forms(client):
    collection = FormCollection(client.app.session())
    collection.definitions.add('Content', definition=textwrap.dedent("""
        E-Mail *= @@@
        Content = <markdown>
    """), type='custom')

    transaction.commit()

    page = client.get('/forms').click('Content')
    page.form['e_mail'] = 'info@example.org'
    page.form['content'] = '<script>alert();</script>'
    page = page.form.submit().follow()

    assert '<script>alert' not in page
    assert '&lt;script&gt;alert' in page
