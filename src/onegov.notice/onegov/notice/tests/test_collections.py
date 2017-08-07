from onegov.notice import OfficialNoticeCollection
from transaction import commit


def test_notice_collection(session):
    notices = OfficialNoticeCollection(session)
    assert notices.query().count() == 0

    notice_1 = notices.add(
        title='Important Announcement',
        text='<em>Important</em> things happened!',
        category='important'
    )
    notice_1.submit()
    notice_1.accept()
    notice_1.publish()

    commit()

    notice_1 = notices.query().one()
    assert notice_1.title == 'Important Announcement'
    assert notice_1.text == '<em>Important</em> things happened!'
    assert notice_1.category == 'important'

    notice_2 = notices.add(
        title='Important Announcement',
        text='<em>Important</em> things happened!'
    )
    notice_2.submit()

    assert notices.query().count() == 2
    assert notices.for_state('drafted').query().count() == 0
    assert notices.for_state('submitted').query().count() == 1
    assert notices.for_state('accepted').query().count() == 0
    assert notices.for_state('published').query().count() == 1

    assert notices.by_name('important-announcement')
    assert notices.by_name('important-announcement-1')

    assert notices.by_id(notice_1.id)
    assert notices.by_id(notice_2.id)

    notices.delete(notice_1)
    notices.delete(notice_2)

    assert notices.query().count() == 0
    assert notices.for_state('drafted').query().count() == 0
    assert notices.for_state('submitted').query().count() == 0
    assert notices.for_state('accepted').query().count() == 0
    assert notices.for_state('published').query().count() == 0


def test_notice_collection_pagination(session):
    notices = OfficialNoticeCollection(session)

    assert notices.page_index == 0
    assert notices.pages_count == 0
    assert notices.batch == []

    for year in range(2008, 2013):
        for month in range(1, 13):
            notice = notices.add(
                title='Notice {0}-{1}'.format(year, month),
                text='text'
            )
            if 2009 <= year:
                notice.submit()
            if 2010 <= year <= 2011:
                notice.accept()
            if 2011 <= year <= 2011:
                notice.publish()
            if 2012 <= year:
                notice.reject()

    assert notices.query().count() == 60

    drafted = notices.for_state('drafted')
    assert drafted.subset_count == 12
    assert len(drafted.next.batch) == 12 - drafted.batch_size

    submitted = notices.for_state('submitted')
    assert submitted.subset_count == 12
    assert len(submitted.next.batch) == 12 - submitted.batch_size

    accepted = notices.for_state('accepted')
    assert accepted.subset_count == 12
    assert len(accepted.next.batch) == 12 - accepted.batch_size

    published = notices.for_state('published')
    assert published.subset_count == 12
    assert len(published.next.batch) == 12 - published.batch_size

    rejected = notices.for_state('rejected')
    assert rejected.subset_count == 12
    assert len(rejected.next.batch) == 12 - rejected.batch_size
