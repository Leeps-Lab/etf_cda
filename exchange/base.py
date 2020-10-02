import enum

from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericRelation
from django.utils import timezone

class BaseExchange(models.Model):
    '''this model is the base model which all oTree Markets exchange implementations should inherit from
    
    it provides a foreign key `group` which references the current group object, and querysets `orders`
    and `trades` which contain all the orders and trades associated with this exchange respectively.
    
    the methods defined on BaseExchange define the API that oTree Markets is expecting from the exchange.
    as long as these methods are defined, the exchange will work correctly with the rest of the system.
    '''

    class Meta:
        app_label = 'otree_markets'
        abstract = True
        unique_together = ('asset_name', 'content_type', 'object_id')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    '''used to relate this exchange to an arbitrary Group'''
    object_id = models.PositiveIntegerField()
    '''primary key of this exchange's related Group'''
    group = GenericForeignKey('content_type', 'object_id')
    '''the Group this exchange is associated with'''

    asset_name = models.CharField(max_length=32)
    '''a unique name for the asset traded in this exchange'''

    orders = GenericRelation('Order')
    '''a queryset of all the orders associated with this exchange'''
    trades = GenericRelation('Trade')
    '''a queryset of all the trades associated with this exchange'''

    def enter_order(self, price, volume, is_bid, pcode):
        '''enter a regular bid or ask into the exchange'''
        pass
    
    def enter_market_order(self, volume, is_bid, pcode):
        '''enter a market order into the exchange
        
        a market bid has effective price 0 and a market ask has effective price infinity.
        additionally, market orders are not entered into the book if they don't immediately
        transact'''
        pass

    def cancel_order(self, order_id):
        '''cancel an already entered order'''
        pass
    
    def accept_immediate(self, accepted_order_id, taker_pcode):
        '''directly trade with the order with id `accepted_order_id`'''
        pass


class OrderStatusEnum(enum.IntEnum):
    ACTIVE         = enum.auto()
    '''this order is currently on the market, available to be traded with'''
    CANCELED       = enum.auto()
    '''this order was canceled'''
    TRADED_TAKER   = enum.auto()
    '''this order was part of a regular trade where it was the taker'''
    TRADED_MAKER   = enum.auto()
    '''this order was part of a regular trade where it was the maker'''
    ACCEPTED_TAKER = enum.auto()
    '''this order was part of an immediate accept trade where it was the taker'''
    ACCEPTED_MAKER = enum.auto()
    '''this order was part of an immediate accept trade where it was the maker'''
    MARKET_TAKER   = enum.auto()
    '''this order was a market order (taker in a market order trade)'''
    MARKET_MAKER   = enum.auto()
    '''this order was traded with a market order'''


class Order(models.Model):
    '''this model represents a single order in an exchange'''

    class Meta:
        app_label = 'otree_markets'
        ordering = ['timestamp']

    # Order has a field 'id' which is referenced often. this is built into django and is
    # a unique identifier associated with each order

    timestamp = models.DateTimeField(default=timezone.now)
    '''this time this order was created'''
    status    = models.PositiveSmallIntegerField(default=OrderStatusEnum.ACTIVE)
    '''this order's current state

    all possible values of this field are in exchange.base.OrderStatusEnum.
    each state is described in that enum
    '''
    price     = models.IntegerField()
    '''this order's price'''
    volume    = models.IntegerField()
    '''this order's volume'''
    is_bid    = models.BooleanField()
    '''true if this is a bid, false if it's an ask'''
    pcode     = models.CharField(max_length=32)
    '''the participant code for the player who submitted this order'''
    traded_volume = models.IntegerField(null=True)
    '''the portion of this trade's volume which was actually traded

    this is used for partially filled orders
    '''
    making_trade  = models.ForeignKey('Trade', null=True, related_name='making_orders', on_delete=models.CASCADE)
    '''if this field is not null, then it references a trade where this order was in the market when the trade occurred'''
    time_inactive = models.DateTimeField(null=True)
    '''the time that this order's status changed from active to something else
    
    null while this order is active
    '''

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    '''used to relate this order to an arbitrary exchange'''
    object_id = models.PositiveIntegerField()
    '''primary key of this order's related exchange'''
    exchange = GenericForeignKey('content_type', 'object_id')
    '''the exchange this order is associated with'''

    # Order will have a related name 'taking_trade' from Trade if this order immediately transacted when it was entered
    # if an order has transacted, then either making_trade or taking_trade will be set

    def as_dict(self):
        '''returns a dict representation of this order'''
        return {
            'timestamp': self.timestamp.timestamp(),
            'price': self.price,
            'volume': self.volume,
            'is_bid': self.is_bid,
            'pcode': self.pcode,
            'traded_volume': self.traded_volume,
            'order_id': self.id,
            'asset_name': self.exchange.asset_name,
        }

    def __str__(self):
        return '{}, {}@${}{}, {}'.format(
            'BID' if self.is_bid else 'ASK',
            self.volume,
            self.price,
            ', traded {}'.format(self.traded_volume) if self.traded_volume else '',
            self.pcode,
        )


class Trade(models.Model):
    '''this model represents a single trade'''

    class Meta:
        app_label = 'otree_markets'
        ordering = ['timestamp']

    timestamp = models.DateTimeField(default=timezone.now)
    '''the time this trade occured'''
    taking_order = models.OneToOneField('Order', related_name='taking_trade', on_delete=models.CASCADE)
    '''the order that triggered this trade'''

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    '''used to relate this trade to an arbitrary exchange'''
    object_id = models.PositiveIntegerField()
    '''primary key of this trade's related exchange'''
    exchange = GenericForeignKey('content_type', 'object_id')
    '''the exchange this trade occurred in'''

    # trades have a related name 'making_orders' from Order. this is a set of all the orders involved in this trade
    # which were already in the market when the trade occurred

    def as_dict(self):
        return {
            'timestamp': self.timestamp.timestamp(),
            'asset_name': self.exchange.asset_name,
            'taking_order': self.taking_order.as_dict(),
            'making_orders': [o.as_dict() for o in self.making_orders.prefetch_related('exchange').all()],
        }

    def __str__(self):
        return (
            'taking order:\n' +
            '{}\n' +
            'making orders:\n' +
            '{}\n'
        ).format(
            self.taking_order,
            '\n'.join(' ' + str(o) for o in self.making_orders.all())
        )