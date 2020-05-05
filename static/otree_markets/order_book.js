import { PolymerElement, html } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';

class OrderBook extends PolymerElement {

    static get properties() {
        return {
            bids: Array,
            asks: Array,
            trades: Array,
            settledAssets: {
                type: Object,
                notify: true,
            },
            availableAssets: {
                type: Object,
                notify: true,
            },
            settledCash: {
                type: Number,
                notify: true,
            },
            availableCash: {
                type: Number,
                notify: true,
            },
        }
    }

    static get template() {
        return html`
            <otree-constants
                id="constants"
            ></otree-constants>
        `;
    }

    ready() {
        super.ready();
        this.pcode = this.$.constants.participantCode;
    }

    // compare two order objects. sort first by price, then by timestamp
    // return a positive or negative number a la c strcmp
    _compare_orders(o1, o2) {
        if (o1.price == o2.price)
            // sort by descending timestamp
            return -(o1.timestamp - o2.timestamp);
        else
            return o1.price - o2.price;
    }

    insert_order(order) {
        if (order.is_bid) {
            this._insert_bid(order);
        }
        else {
            this._insert_ask(order);
        }
    }

    // insert an order into the bids array in descending order
    _insert_bid(order) {
        let i = 0;
        for (; i < this.bids.length; i++) {
            if (this._compare_orders(this.bids[i], order) < 0)
                break;
        }
        this.splice('bids', i, 0, order);

        if (order.pcode == this.pcode) {
            this.availableCash -= order.price * order.volume;
        }
    }

    // insert an ask into the asks array in ascending order
    _insert_ask(order) {
        let i = 0;
        for (; i < this.asks.length; i++) {
            if (this._compare_orders(this.asks[i], order) > 0)
                break;
        }
        this.splice('asks', i, 0, order);

        if (order.pcode == this.pcode) {
            this._update_subproperty('availableAssets', order.asset_name, -order.volume);
        }
    }

    // remove an order from either the bids list or the asks list
    remove_order(order) {
        const order_store_name = order.is_bid ? 'bids' : 'asks';
        const order_store = this.get(order_store_name);
        let i = 0;
        for (; i < order_store.length; i++)
            if (order_store[i].order_id == order.order_id)
                break;
        if (i >= order_store.length) {
            console.warn(`order with id ${order.order_id} not found in ${order_store_name}`);
            return;
        }
        this.splice(order_store_name, i, 1);

        if (order.pcode == this.pcode) {
            if (order.is_bid) {
                this.availableCash += order.price * order.volume;
            }
            else {
                this._update_subproperty('availableAssets', order.asset_name, order.volume);
            }
        }
    }

    handle_trade(making_orders, taking_order, asset_name, timestamp) {
        // list of order dicts that belong to this trader and that were involved in this trade
        const my_trades = [];
        
        // iterate through making orders from this trade. if a making order is yours or the taking order is yours,
        // update your cash and assets appropriately
        for (const making_order of making_orders) {
            if (making_order.pcode == this.pcode) {
                my_trades.push(making_order)
                this._update_holdings(making_order.price, making_order.traded_volume, making_order.is_bid, making_order.asset_name);
            }
            if (taking_order.pcode == this.pcode) {
                this._update_holdings(making_order.price, making_order.traded_volume, taking_order.is_bid, taking_order.asset_name);
            }
            this.remove_order(making_order)
        }
        if (taking_order.pcode == this.pcode) {
            my_trades.push(taking_order)
        }

        // make a new trade object and sorted-ly insert it into the trades list
        const trade = {
            timestamp: timestamp,
            asset_name: asset_name,
            taking_order: taking_order,
            making_orders: making_orders,
        }
        let i;
        for (; i < this.trades.length; i++)
            if (this.trades[i].timestamp > msg.timestamp)
                break;
        this.splice('trades', i, 0, trade);

        return my_trades;
    }

    _update_holdings(price, volume, is_bid, asset_name) {
        if (is_bid) {
            this._update_subproperty('availableAssets', asset_name, volume);
            this._update_subproperty('settledAssets', asset_name, volume);

            this.availableCash -= price * volume;
            this.settledCash -= price * volume;
        }
        else {
            this._update_subproperty('availableAssets', asset_name, -volume);
            this._update_subproperty('settledAssets', asset_name, -volume);

            this.availableCash += price * volume;
            this.settledCash += price * volume;
        }
    }

    _update_subproperty(property, subproperty, amount) {
        const old = this.get([property, subproperty]);
        this.set([property, subproperty], old + amount);
    }

}

window.customElements.define('order-book', OrderBook);
