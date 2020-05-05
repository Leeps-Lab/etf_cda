from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from itertools import chain

class Exchange(models.Model):
    '''this model represents a continuous double auction exchange'''

    # Exchange has additional fields 'trades' and 'orders'
    # these are related names from ForeignKey fields on Trade and Order

    class Meta:
        app_label = 'otree_markets'
        unique_together = ('asset_name', 'content_type', 'object_id')

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    '''used to relate this Exchange to an arbitrary Group'''
    object_id = models.PositiveIntegerField()
    '''primary key of this Exchange's related Group'''
    group = GenericForeignKey('content_type', 'object_id')
    '''the Group this exchange is associated with'''

    asset_name = models.CharField(max_length=32)
    '''a unique name for the asset traded in this exchange'''
    
    def _get_bids_qset(self):
        '''get a queryset of the bids held by this exchange, sorted by descending price then timestamp'''
        return (self.orders.filter(is_bid=True, active=True)
                           .order_by('-price', 'timestamp'))

    def _get_asks_qset(self):
        '''get a queryset of the asks held by this exchange, sorted by ascending price then timestamp'''
        return (self.orders.filter(is_bid=False, active=True)
                           .order_by('price', 'timestamp'))
    
    def _get_best_bid(self):
        '''get the best bid in this exchange'''
        return self._get_bids_qset().first()
    
    def _get_best_ask(self):
        '''get the best ask in this exchange'''
        return self._get_asks_qset().first()
    
    def _get_trades_qset(self):
        '''get a queryset of all trades that have occurred in this exchange, ordered by timestamp'''
        return (self.trades.order_by('timestamp')
                           .prefetch_related('taking_order', 'making_orders'))
    
    def _get_order(self, is_bid, order_id):
        orders = self._get_bids_qset() if is_bid else self._get_asks_qset()
        try:
            return orders.get(id=order_id)
        except Order.DoesNotExist as e:
            raise ValueError('order with id {} not found'.format(order_id)) from e

    def enter_order(self, price, volume, is_bid, pcode):
        '''enter a bid or ask into the exchange'''
        order = self.orders.create(
            price  = price,
            volume = volume,
            is_bid = is_bid,
            pcode  = pcode
        )

        if is_bid:
            self._handle_insert_bid(order)
        else:
            self._handle_insert_ask(order)
    
    def cancel_order(self, is_bid, order_id):
        '''cancel an already entered order'''
        canceled_order = self._get_order(is_bid, order_id)
        canceled_order.active = False
        canceled_order.save()
        self.group.confirm_cancel(canceled_order.as_dict())
    
    def accept_immediate(self, accepted_is_bid, accepted_order_id, taker_pcode):
        '''create a new order and trade it with the order with id `order_id`'''
        accepted_order = self._get_order(accepted_is_bid, accepted_order_id)

        taking_order = self.orders.create(
            active = False,
            price  = accepted_order.price,
            volume = accepted_order.volume,
            is_bid = not accepted_is_bid,
            pcode  = taker_pcode,
            traded_volume = accepted_order.volume,
        )

        trade = self.trades.create(taking_order=taking_order)

        accepted_order.active = False
        accepted_order.making_trade = trade
        accepted_order.traded_volume = accepted_order.volume
        accepted_order.save()

        self._send_trade_confirmation(trade)
    
    def _handle_insert_bid(self, bid_order):
        '''handle a bid being inserted into the order book, transacting if necessary'''
        # if this order isn't aggressive enough to transact with the best ask, just enter it
        best_ask = self._get_best_ask()
        if not best_ask or bid_order.price < best_ask.price:
            self._send_enter_confirmation(bid_order)
            return

        asks = self._get_asks_qset()
        trade = self.trades.create(taking_order=bid_order)
        cur_volume = bid_order.volume
        for ask in asks:
            if cur_volume == 0 or bid_order.price < ask.price:
                break
            if cur_volume >= ask.volume:
                cur_volume -= ask.volume
                ask.traded_volume = ask.volume
            else:
                self._enter_partial(ask, ask.volume - cur_volume)
                ask.traded_volume = cur_volume
                cur_volume = 0
            ask.making_trade = trade
            ask.active = False
            ask.save()
        if cur_volume > 0:
            self._enter_partial(bid_order, cur_volume)
        bid_order.traded_volume = bid_order.volume - cur_volume
        bid_order.active = False
        bid_order.save()
        self._send_trade_confirmation(trade)
    
    def _handle_insert_ask(self, ask_order):
        '''handle an ask being inserted into the order book, transacting if necessary'''
        # if this order isn't aggressive enough to transact with the best bid, just enter it
        best_bid = self._get_best_bid()
        if not best_bid or ask_order.price > best_bid.price:
            self._send_enter_confirmation(ask_order)
            return

        bids = self._get_bids_qset()
        trade = self.trades.create(taking_order=ask_order)
        cur_volume = ask_order.volume
        for bid in bids:
            if cur_volume == 0 or ask_order.price > bid.price :
                break
            if cur_volume >= bid.volume:
                cur_volume -= bid.volume
                bid.traded_volume = bid.volume
            else:
                self._enter_partial(bid, bid.volume - cur_volume)
                bid.traded_volume = cur_volume
                cur_volume = 0
            bid.making_trade = trade
            bid.active = False
            bid.save()
        if cur_volume > 0:
            self._enter_partial(ask_order, cur_volume)
        ask_order.traded_volume = ask_order.volume - cur_volume
        ask_order.active = False
        ask_order.save()
        self._send_trade_confirmation(trade)
    
    def _enter_partial(self, order, new_volume):
        '''reenter an order that's been partially filled'''
        new_order = self.orders.create(
            timestamp = order.timestamp,
            price     = order.price,
            volume    = new_volume,
            is_bid    = order.is_bid,
            pcode     = order.pcode
        )
        self._send_enter_confirmation(new_order)
    
    def _send_enter_confirmation(self, order):
        '''send an order enter confirmation to the group'''
        self.group.confirm_enter(order.as_dict())

    def _send_trade_confirmation(self, trade):
        '''send a trade confirmation to the group'''
        taking_order = trade.taking_order.as_dict()
        making_orders = trade.get_making_orders_dicts()
        self.group.handle_trade(
            timestamp     = trade.timestamp.timestamp(),
            asset_name    = self.asset_name,
            taking_order  = taking_order,
            making_orders = making_orders,
        )
    
    def __str__(self):
        return '\n'.join(' ' + str(e) for e in chain(self._get_bids_qset(), self._get_asks_qset()))


class Order(models.Model):
    '''this model represents a single order in an exchange'''

    class Meta:
        app_label = 'otree_markets'

    # Order has a field 'id' which is referenced often. this is built into django and is
    # a unique identifier associated with each order

    # this time this order was created
    timestamp = models.DateTimeField(auto_now_add=True)
    # whether this order is still active
    active    = models.BooleanField(default=True)
    # this order's price
    price     = models.IntegerField()
    # this order's volume
    volume    = models.IntegerField()
    # true if this is a bid, false if it's an ask
    is_bid    = models.BooleanField()
    # the exchange object associated with this order
    exchange  = models.ForeignKey(Exchange, related_name='orders', on_delete=models.CASCADE)
    # the participant code for the player who submitted this order
    pcode     = models.CharField(max_length=16)
    # the portion of this trade's volume which was actually traded
    # this is used for partially filled orders
    traded_volume = models.IntegerField(null=True)
    # if this field is not null, then it references a trade where this order was in the market when the trade occurred
    making_trade  = models.ForeignKey('Trade', null=True, related_name='making_orders', on_delete=models.CASCADE)

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

    # the time this trade occured
    timestamp = models.DateTimeField(auto_now_add=True)
    # the exchange this trade happened in
    exchange  = models.ForeignKey('Exchange', related_name='trades', on_delete=models.CASCADE)
    # this is the order that triggered this trade
    taking_order = models.OneToOneField('Order', related_name='taking_trade', on_delete=models.CASCADE)
    # trades have a related name 'making_orders' from Order. this is a set of all the orders involved in this trade
    #  which were already in the market when the trade occurred

    def get_making_orders_dicts(self):
        '''returns a list of dict representations of all the making orders for this trade'''
        return [o.as_dict() for o in self.making_orders.select_related('exchange').all()]

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
