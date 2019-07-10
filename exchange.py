from django.db import models

class Exchange(models.Model):

    class Meta:
        app_label = 'etf_cda'

    # the group object associated with this exchange
    group = models.ForeignKey('etf_cda.Group', related_name='exchanges', on_delete=models.CASCADE)
    
    # handle incoming messages
    def handle_msg_in(self, msg):
        order = Order.objects.create(
            price    = msg['price'],
            is_bid   = msg['is_bid'],
            pcode    = msg['pcode'],
            exchange = self,
        )

        self._calc_crossing()
    
    # get a list of the bids held by this exchange, sorted by ascending price then timestamp
    def _get_bids(self):
        return list(self.orders.filter(is_bid=False)
                               .order_by('price', 'timestamp'))

    # get a list of the asks held by this exchange, sorted by descending price then timestamp
    def _get_asks(self):
        return list(self.orders.filter(is_bid=True)
                               .order_by('-price', 'timestamp'))

    # check the current order book for crossings and emit trades if necessary
    def _calc_crossing(self):
        print(self._get_asks())
        print(self._get_bids())

# this model represents a single order in an exchange
class Order(models.Model):

    class Meta:
        app_label = 'etf_cda'

    # this time this order was created
    timestamp = models.DateTimeField(auto_now_add=True)
    # this order's price
    price     = models.IntegerField()
    # true if this is a bid, false if it's an ask
    is_bid    = models.BooleanField()
    # the exchange object associated with this order
    exchange  = models.ForeignKey(Exchange, related_name='orders', on_delete=models.CASCADE)
    # the participant code for the player who submitted this order
    pcode     = models.CharField(max_length=16)

    def __str__(self):
        return '{}, {}, {}'.format(
            'BID' if self.is_bid else 'ASK',
            self.price,
            self.pcode,
        )
