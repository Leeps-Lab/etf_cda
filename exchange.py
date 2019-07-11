from django.db import models

class Exchange(models.Model):

    # Exchange has additional fields 'trades' and 'orders'
    # these are related names from ForeignKey fields on Trade and Order

    class Meta:
        app_label = 'etf_cda'

    # the group object associated with this exchange
    group = models.ForeignKey('Group', related_name='exchanges', on_delete=models.CASCADE)
    
    # get a queryset of the bids held by this exchange, sorted by ascending price then timestamp
    def _get_bids_qset(self):
        return (self.orders.filter(is_bid=True, active=True)
                          .order_by('-price', 'timestamp'))

    # get a queryset of the asks held by this exchange, sorted by descending price then timestamp
    def _get_asks_qset(self):
        return (self.orders.filter(is_bid=False, active=True)
                          .order_by('price', 'timestamp'))
    
    # get the best bid in this exchange
    def _get_best_bid(self):
        return self._get_bids_qset().first()
    
    # get the best ask in this exchange
    def _get_best_ask(self):
        return self._get_asks_qset().first()

    # enter a bid or ask into the exchange
    def enter_order(self, price, is_bid, pcode):
        print('before insert')
        print(self)
        order = self.orders.create(
            price    = price,
            is_bid   = is_bid,
            pcode    = pcode
        )

        if is_bid:
            self._handle_insert_bid(order)
        else:
            self._handle_insert_ask(order)
        print('after insert')
        print(self)
    
    def _handle_insert_bid(self, order):
        best_ask = self._get_best_ask()

        if best_ask is not None and order.price >= best_ask.price:
            self._handle_trade(bid_order=order, ask_order=best_ask, price=best_ask.price)
    
    def _handle_insert_ask(self, order):
        best_bid = self._get_best_bid()

        if best_bid is not None and order.price <= best_bid.price:
            self._handle_trade(bid_order=best_bid, ask_order=order, price=best_bid.price)

    def _handle_trade(self, bid_order=None, ask_order=None, price=None):
        if None in (bid_order, ask_order, price):
            raise ValueError('invalid trade: bid={}, ask={}, price={}'.format(bid_order, ask_order, price))

        trade = self.trades.create(
            price     = price,
            bid_order = ask_order,
            ask_order = ask_order
        )

        bid_order.active = False
        bid_order.trade  = trade
        bid_order.save()
        ask_order.active = False
        ask_order.trade  = trade
        ask_order.save()

        self.group.handle_trade(
            price     = price,
            bid_pcode = bid_order.pcode,
            ask_pcode = ask_order.pcode
        )
    
    def __str__(self):
        result  = 'bids:\n'
        result += '\n'.join('\t' + str(e) for e in self._get_bids_qset())
        result += 'asks:\n'
        result += '\n'.join('\t' + str(e) for e in self._get_asks_qset())
        return result


# this model represents a single order in an exchange
class Order(models.Model):

    class Meta:
        app_label = 'etf_cda'

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


# this model represents a single trade
class Trade(models.Model):

    class Meta:
        app_label = 'etf_cda'

    # the time this trade occured
    timestamp = models.DateTimeField(auto_now_add=True)
    # this price this trade occurred at
    price     = models.IntegerField()
    # the exchange this trade happened in
    exchange  = models.ForeignKey('Exchange', related_name='trades', on_delete=models.CASCADE)
    # the bid order from this trade
    bid_order = models.OneToOneField(Order, related_name='+', on_delete=models.CASCADE)
    # the ask order from this trade
    ask_order = models.OneToOneField(Order, related_name='+', on_delete=models.CASCADE)
