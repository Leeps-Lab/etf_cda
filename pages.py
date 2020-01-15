from otree.api import Currency as c, currency_range
from . import models
from ._builtin import Page, WaitPage
from .models import Constants


class Market(Page):

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds


class ResultsWaitPage(WaitPage):

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds


class Results(Page):

    def is_displayed(self):
        return self.round_number < self.subsession.config.num_rounds

page_sequence = [
    Market,
    ResultsWaitPage,
    Results
]
