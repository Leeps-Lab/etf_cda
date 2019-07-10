from django.db import models

class Exchange(models.Model):

    class Meta:
        app_label = 'etf_cda'

    group = models.ForeignKey('etf_cda.Group', related_name='exchanges', on_delete=models.CASCADE)
    
    def get_bids(self):
        return list(self.orders.filter(is_bid=True).order_by('price'))

    def get_asks(self):
        return list(self.orders.filter(is_bid=False).order_by('-price'))

    def handle_order_in(self, msg):
        order = Order.objects.create(
            price    = msg['price'],
            is_bid   = msg['is_bid'],
            pcode    = msg['pcode'],
            exchange = self,
        )

        self._calc_crossing()
    
    def _calc_crossing(self):
        print(self.get_asks())
        print(self.get_bids())

class Order(models.Model):

    class Meta:
        app_label = 'etf_cda'

    timestamp = models.DateTimeField(auto_now_add=True)
    price     = models.IntegerField()
    is_bid    = models.BooleanField()
    exchange  = models.ForeignKey(Exchange, related_name='orders', on_delete=models.CASCADE)
    pcode     = models.CharField(max_length=16)

    def __str__(self):
        return '{}, {}, {}'.format(
            'BID' if self.is_bid else 'ASK',
            self.price,
            self.pcode,
        )
