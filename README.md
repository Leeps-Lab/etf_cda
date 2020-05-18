# oTree Markets
### A generic market implementation in oTree

oTree Markets is an oTree app which is meant to be an easily modifiable reference implementation of a market experiment, created using LEEPS lab's [redwood](https://github.com/Leeps-Lab/otree-redwood) framework for realtime communication in oTree. It consists of 3 main components:
  - a CDA market implementation (contained in [exchange.py](./exchange.py)) with support for multiple unit orders
  - an oTree app (contained in [models.py](./models.py) and [pages.py](./pages.py)) which maintains records of players' cash and asset allocations and coordinates communication between the exchange and the frontend 
  - a set of reusable webcomponents for creating market frontends (contained in this experiment's [static files](./static/otree_markets/))
  
This repo is not an oTree app, it is a set of base classes and Polymer.js components which can be used to create a market experiment in oTree. To see a fully-realized market experiment built using oTree Markets, check out our [single asset market](https://github.com/Leeps-Lab/otree_single_asset_market) or [multiple asset market](https://github.com/Leeps-Lab/otree_multiple_asset_market) implementations.

This project was started by Morgan Grant in fulfillment of his Masters project. You can read the writeup paper for that [here](https://leeps.ucsc.edu/media/papers/project_writeup.pdf)

For documentation, check out the (wiki)[https://github.com/Leeps-Lab/otree_markets/wiki]
