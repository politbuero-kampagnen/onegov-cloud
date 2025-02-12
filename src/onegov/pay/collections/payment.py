from collections import defaultdict
from onegov.core.collection import GenericCollection, Pagination
from onegov.pay.models import Payment
from sqlalchemy import desc
from sqlalchemy.orm import joinedload
from sqlalchemy.orm import undefer


class PaymentCollection(GenericCollection, Pagination):
    """ Manages the payment records.

    To render a list of payments you might want to also consider the
    :class:`onegov.pay.collection.payable.Paybale` collection, which renders
    payments by loading the linked records first.

    """

    def __init__(self, session, source='*', page=0, start=None, end=None):
        super().__init__(session)
        self.source = source
        self.page = page
        self.start = start
        self.end = end

    @property
    def model_class(self):
        return Payment.get_polymorphic_class(self.source, Payment)

    def add(self, **kwargs):
        if self.source != '*':
            kwargs.setdefault('source', self.source)
        return super().add(**kwargs)

    def __eq__(self, other):
        return all((
            self.source == other.source,
            self.page == other.page,
            self.start == other.start,
            self.end == other.end
        ))

    def subset(self):
        q = self.query().order_by(desc(Payment.created))

        if self.start:
            q = q.filter(self.start <= Payment.created)

        if self.end:
            q = q.filter(Payment.created <= self.end)

        q = q.options(joinedload(Payment.provider))
        q = q.options(undefer(Payment.created))
        return q

    @property
    def page_index(self):
        return self.page

    def page_by_index(self, index):
        return self.__class__(self.session, self.source, index)

    def payment_links_for(self, items):
        """ A more efficient way of loading all links of the given batch
              (compared to loading payment.links one by one).

        """
        payment_links = defaultdict(list)

        for link in Payment.registered_links.values():
            targets = self.session.query(
                getattr(link.table.columns, link.key)
            ).filter(
                link.table.columns.payment_id.in_(tuple(
                    p.id for p in items
                ))
            )

            q = self.session.query(link.cls)
            q = q.filter(link.cls.id.in_(targets.subquery()))
            q = q.options(joinedload(link.class_attribute))

            for record in q:
                payments = getattr(record, link.attribute)

                try:
                    for payment in payments:
                        payment_links[payment.id].append(record)
                except TypeError:
                    payment_links[payments.id].append(record)

        return payment_links

    def payment_links_by_subset(self, subset=None):
        subset = subset or self.subset()
        return self.payment_links_for(subset)

    def payment_links_by_batch(self, batch=None):
        batch = batch or self.batch

        if not batch:
            return None

        return self.payment_links_for(batch)
