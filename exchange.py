from django.db import models
from itertools import chain

class Exchange(models.Model):

    # Exchange has additional fields 'trades' and 'orders'
    # these are related names from ForeignKey fields on Trade and Order

    class Meta:
        app_label = 'otree_markets'
        unique_together = ['group', 'asset_name']

    # the group object associated with this exchange
    group = models.ForeignKey('Group', related_name='exchanges', on_delete=models.CASCADE)
    # a unique name for this exchange
    asset_name = models.CharField(max_length=16)
    
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
                           .select_related('bid_order', 'ask_order'))

    def enter_order(self, price, is_bid, pcode):
        '''enter a bid or ask into the exchange'''
        print('before insert')
        print(self)
        order = self.orders.create(
            price  = price,
            is_bid = is_bid,
            pcode  = pcode
        )

        if is_bid:
            self._handle_insert_bid(order)
        else:
            self._handle_insert_ask(order)
        
        print('after insert')
        print(self)
    
    def cancel_order(self, is_bid, order_id):
        orders = self._get_bids_qset() if is_bid else self._get_asks_qset()
        canceled_order = orders.get(id=order_id)
        canceled_order.active = False
        canceled_order.save(update_fields=['active'])
        self.group.confirm_cancel(
            order_id   = order_id,
            is_bid     = is_bid,
            asset_name = self.asset_name
        )
    
    def _handle_insert_bid(self, order):
        best_ask = self._get_best_ask()

        if best_ask is not None and order.price >= best_ask.price:
            self._handle_trade(bid_order=order, ask_order=best_ask, price=best_ask.price)
        else:
            self._send_confirm(order)
    
    def _handle_insert_ask(self, order):
        best_bid = self._get_best_bid()

        if best_bid is not None and order.price <= best_bid.price:
            self._handle_trade(bid_order=best_bid, ask_order=order, price=best_bid.price)
        else:
            self._send_confirm(order)
    
    def _send_confirm(self, order):
        '''send an order enter confirmation to the group'''
        self.group.confirm_enter(
            timestamp  = order.timestamp.timestamp(),
            price      = order.price,
            is_bid     = order.is_bid,
            pcode      = order.pcode,
            asset_name = self.asset_name,
            order_id   = order.id
        )

    def _handle_trade(self, bid_order=None, ask_order=None, price=None):
        if None in (bid_order, ask_order, price):
            raise ValueError('invalid trade: bid={}, ask={}, price={}'.format(bid_order, ask_order, price))

        trade = self.trades.create(
            price     = price,
            bid_order = bid_order,
            ask_order = ask_order
        )

        bid_order.set_traded(trade)
        ask_order.set_traded(trade)

        self.group.handle_trade(
            timestamp    = trade.timestamp.timestamp(),
            price        = price,
            bid_pcode    = bid_order.pcode,
            ask_pcode    = ask_order.pcode,
            bid_order_id = bid_order.id,
            ask_order_id = ask_order.id,
            asset_name   = self.asset_name,
        )
    
    def __str__(self):
        return '\n'.join(' ' + str(e) for e in chain(self._get_bids_qset(), self._get_asks_qset()))


# this model represents a single order in an exchange
class Order(models.Model):

    class Meta:
        app_label = 'otree_markets'

    # this time this order was created
    timestamp = models.DateTimeField(auto_now_add=True)
    # whether this order is still active
    active    = models.BooleanField(default=True)
    # this order's price
    price     = models.IntegerField()
    # true if this is a bid, false if it's an ask
    is_bid    = models.BooleanField()
    # the exchange object associated with this order
    exchange  = models.ForeignKey(Exchange, related_name='orders', on_delete=models.CASCADE)
    # the participant code for the player who submitted this order
    pcode     = models.CharField(max_length=16)
    # the trade that this order is a part of. null unless the order transacts
    trade     = models.ForeignKey('Trade', related_name='+', null=True, on_delete=models.CASCADE)

    def __str__(self):
        return '{}, {}, {}'.format(
            'BID' if self.is_bid else 'ASK',
            self.price,
            self.pcode,
        )

    def set_traded(self, trade):
        '''marks this order as inactive and sets its trade field'''
        self.active = False
        self.trade = trade
        self.save(update_fields=['active', 'trade'])


# this model represents a single trade
class Trade(models.Model):

    class Meta:
        app_label = 'otree_markets'

    # the time this trade occured
    timestamp = models.DateTimeField(auto_now_add=True)
    # this price this trade occurred at
    price     = models.IntegerField()
    # the exchange this trade happened in
    exchange  = models.ForeignKey('Exchange', related_name='trades', on_delete=models.CASCADE)
    # the bid order from this trade
    bid_order = models.OneToOneField('Order', related_name='+', on_delete=models.CASCADE)
    # the ask order from this trade
    ask_order = models.OneToOneField('Order', related_name='+', on_delete=models.CASCADE)
