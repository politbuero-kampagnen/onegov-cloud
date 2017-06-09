from collections import namedtuple
from decimal import Decimal
from functools import total_ordering
from sqlalchemy_utils import QueryChain as QueryChainBase


class QueryChain(QueryChainBase):
    """ Extends SQLAlchemy Utils' QueryChain with some extra methods. """

    def slice(self, start, end):
        return self[start:end]

    def first(self):
        return next((o for o in self), None)

    def all(self):
        return tuple(self)


@total_ordering
class Price(namedtuple('PriceBase', ('amount', 'currency'))):
    """ A single price. """

    def __new__(cls, amount, currency):
        return super().__new__(cls, Decimal(amount), currency)

    def __bool__(self):
        return self.amount and True or False

    def __lt__(self, other):
        return self.amount < other.amount

    def __add__(self, other):
        assert self.currency is None or self.currency == other.currency
        return self.__class__(
            self.amount + other.amount,
            self.currency or other.currency
        )

    def __sub__(self, other):
        assert self.currency == other.currency
        return self.__class__(self.amount - other.amount, self.currency)

    @classmethod
    def zero(cls):
        return cls(0, None)

    def as_dict(self):
        return {
            'amount': float(self.amount),
            'currency': self.currency
        }
