""" Contains upgrade tasks that are executed when the application is being
upgraded on the server. See :class:`onegov.core.upgrade.upgrade_task`.

"""
from onegov.core.upgrade import upgrade_task
from onegov.gazette.models.notice import GazetteNotice


@upgrade_task(
    'Move gazette category IDs',
    requires='onegov.notice:Add categories column to official notices'
)
def migrate_category_ids(context):
    for notice in context.session.query(GazetteNotice):
        if notice.meta:
            if 'category_id' in notice.meta:
                category_id = notice.meta['category_id']
                notice.category_id = category_id
                del notice.meta['category_id']


@upgrade_task(
    'Move gazette organization IDs',
    requires='onegov.notice:Add organizations column to official notices'
)
def migrate_organization_ids(context):
    for notice in context.session.query(GazetteNotice):
        if notice.meta:
            if 'organization_id' in notice.meta:
                organization_id = notice.meta['organization_id']
                notice.organization_id = organization_id
                del notice.meta['organization_id']


@upgrade_task('Migrate gazette categories', always_run=True)
def migrate_categories(context):
    principal = getattr(context.app, 'principal', None)
    if not principal:
        return False

    categories = getattr(principal, '_categories', None)
    if not categories:
        return False

    if not context.has_table('gazette_categories'):
        return False

    session = context.app.session_manager.session()
    count = session.execute("select count(*) from gazette_categories")
    if count.scalar() != 0:
        return False

    collection = CategoryCollection(session)
    for name, title in categories.items():
        collection.add_root(name=name, title=title, active=True)


@upgrade_task('Migrate gazette organizations', always_run=True)
def migrate_organizations(context):
    principal = getattr(context.app, 'principal', None)
    if not principal:
        return False

    organizations = getattr(principal, '_organizations', None)
    if not organizations:
        return False

    if not context.has_table('gazette_organizations'):
        return False

    session = context.app.session_manager.session()
    session.execute("delete from gazette_organizations")  # todo: remove me!!!!
    count = session.execute("select count(*) from gazette_organizations")
    if count.scalar() != 0:
        return False

    collection = OrganizationCollection(session)
    for index, name in enumerate(organizations):
        collection.add_root(
            name=name,
            title=organizations[name],
            active=True,
            order=index
        )
