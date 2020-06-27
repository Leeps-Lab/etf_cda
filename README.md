# oTree Markets
### A generic market implementation in oTree

oTree Markets is an extension to oTree which provides a set of useful tools for the creation of market-based experiments. It was built on LEEPS lab's [redwood](https://github.com/Leeps-Lab/otree-redwood) framework for realtime communication. It consists of 3 main components:
  - a CDA market implementation (contained in [cda_exchange.py](./cda_exchange.py)) with support for multiple unit orders
  - extended versions of oTree models and views (contained in [models.py](./models.py) and [pages.py](./pages.py)) which maintain records of players' cash and asset allocations and coordinates communication between the exchange and the frontend 
  - a Javascript trading interface, as well as a set of reusable webcomponents for creating market GUIs (contained in the [static files](./static/otree_markets/))

To see some market experiments built using oTree Markets, check out our [single asset market](https://github.com/Leeps-Lab/otree_single_asset_market) or [multiple asset market](https://github.com/Leeps-Lab/otree_multiple_asset_market) implementations. A more complex example can be found in our [market with ETF](https://github.com/Leeps-Lab/otree_etf_cda) experiment. This experiment overrides some of oTree Markets' functionality to add support for an ETF asset, as well as automated trading bots.

This project was started by Morgan Grant in fulfillment of his Masters project. You can read the writeup paper for that [here](https://leeps.ucsc.edu/media/papers/project_writeup.pdf)

To get started with oTree Markets, check out the [wiki](https://github.com/Leeps-Lab/otree_markets/wiki)
