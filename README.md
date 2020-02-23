# otree_markets
### A generic market implementation in oTree

`otree_markets` is an oTree app which is meant to be an easily modifiable reference implementation of a market experiment, created using LEEPS lab's [redwood](https://github.com/Leeps-Lab/otree-redwood) framework for realtime communication in oTree. It consists of 3 main components:
  - a CDA market implementation (contained in [exchange.py](./exchange.py)) with support for multiple unit orders
  - an oTree app (contained in [models.py](./models.py) and [pages.py](./pages.py)) which maintains records of players' cash and asset allocations and coordinates communication between the exchange and the frontend 
  - a basic text-based javascript frontend (contained in this experiment's [static files](./static/otree_markets/text_interface))
  
  The oTree app and exchange have support for multiple-asset trading situations, though the provided text interface is currently only configured for a single asset. Finishing multiple asset support is an immediate goal for this project.
