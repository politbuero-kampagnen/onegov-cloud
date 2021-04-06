from onegov.recipient.collection import GenericRecipientCollection
from onegov.recipient.model import GenericRecipient


def test_recipient_model_order(session):

    session.add(GenericRecipient(
        name="Peter's Url",
        medium="http",
        address="http://example.org/push",
        extra="POST"
    ))

    session.add(GenericRecipient(
        name="Peter's Cellphone",
        medium="phone",
        address="+12 345 67 89"
    ))

    session.add(GenericRecipient(
        name="Peter's E-Mail",
        medium="email",
        address="peter@example.org"
    ))

    session.flush()

    email, phone, url = session.query(GenericRecipient).order_by(
        GenericRecipient.order).all()
    assert email.order == 'peter-s-cellphone'
    assert phone.order == 'peter-s-e-mail'
    assert url.order == 'peter-s-url'


def test_recipient_collection(session):

    class FooRecipient(GenericRecipient):
        __mapper_args__ = {'polymorphic_identity': 'foo'}

    class BarRecipient(GenericRecipient):
        __mapper_args__ = {'polymorphic_identity': 'bar'}

    bar_recipients = GenericRecipientCollection(session, type='bar')
    bar_recipients.add(
        name="Hidden recipient",
        medium="phone",
        address="+12 345 67 89"
    )
    bar_recipients.add(
        name="Forbidden recipient",
        medium="phone",
        address="+12 345 67 89"
    )
    # test sorting
    all_bar = bar_recipients.query().all()
    assert all_bar == sorted(all_bar, key=lambda en: en.order)

    foo_recipients = GenericRecipientCollection(session, type='foo')
    foo = foo_recipients.add(
        name="Peter's Cellphone",
        medium="phone",
        address="+12 345 67 89"
    )

    assert foo_recipients.query().count() == 1
    assert bar_recipients.query().count() == 2

    for obj in (foo, foo_recipients.query().first()):
        assert obj.type == 'foo'
        assert isinstance(obj, FooRecipient)

    foo_recipients.delete(foo)
    assert foo_recipients.query().count() == 0
