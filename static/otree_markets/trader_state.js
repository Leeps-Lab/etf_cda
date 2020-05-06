import { PolymerElement, html } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';

class TraderState extends PolymerElement {

    /*
        this webcomponent is responsible for communicating with the backend and maintaining a single player's
        current state. it has methods which allow the player to enter, remove and accept orders. it also emits events
        on confirmations of market state changes, as well as when errors occur.
    */

    static get properties() {
        return {
            bids: Array,
            asks: Array,
            trades: Array,
            settledAssets: {
                type: Object,
                notify: true,
                reflectToAttribute: true,
            },
            availableAssets: {
                type: Object,
                notify: true,
                reflectToAttribute: true,
            },
            settledCash: {
                type: Number,
                notify: true,
                reflectToAttribute: true,
            },
            availableCash: {
                type: Number,
                notify: true,
                reflectToAttribute: true,
            },
        }
    }

    static get template() {
        return html`
            <redwood-channel
                id="chan"
                channel="chan"
                on-event="_on_message"
            ></redwood-channel>
            <otree-constants
                id="constants"
            ></otree-constants>
        `;
    }

    ready() {
        super.ready();
        this.pcode = this.$.constants.participantCode;

        // maps incoming message types to their appropriate handler
        this.message_handlers = {
            confirm_enter: this._handle_confirm_enter,
            confirm_trade: this._handle_confirm_trade,
            confirm_cancel: this._handle_confirm_cancel,
            error: this._handle_error,
        };
    }

    // call this method to send an order enter message to the backend
    enter_order(order) {
        this.$.chan.send({
            type: 'enter',
            payload: {
                price: order.price,
                volume: order.volume,
                is_bid: order.is_bid,
                asset_name: order.asset_name,
                pcode: this.pcode,
            }
        });
    }

    // call this method to send an order cancel message to the backend
    cancel_order(order) {
        this.$.chan.send({
            type: 'cancel',
            payload: order,
        });
    }

    // call this method to send an immediate accept message to the backend
    accept_order(order) {
        this.$.chan.send({
            type: 'accept_immediate',
            payload: order
        });
    }

    // main entry point for inbound messages. dispatches messages
    // to the appropriate handler
    _on_message(event) {
        const msg = event.detail.payload;
        const handler = this.message_handlers[msg.type];
        if (!handler) {
            throw `error: invalid message type: ${msg.type}`;
        }
        handler.call(this, msg.payload);
    }

    // handle an incoming order entry confirmation
    _handle_confirm_enter(msg) {
        const order = msg;
        if (order.is_bid) {
            this._insert_bid(order);
        }
        else {
            this._insert_ask(order);
        }

        this.dispatchEvent(new CustomEvent('confirm-order-enter', {detail: order, bubbles: true, composed: true}));
    }

    // handle an incoming trade confirmation
    _handle_confirm_trade(msg) {
        // iterate through making orders from this trade. if a making order is yours or the taking order is yours,
        // update your cash and assets appropriately
        for (const making_order of msg.making_orders) {
            if (making_order.pcode == this.pcode) {
                this._update_holdings(making_order.price, making_order.traded_volume, making_order.is_bid, making_order.asset_name);
            }
            if (msg.taking_order.pcode == this.pcode) {
                this._update_holdings(making_order.price, making_order.traded_volume, msg.taking_order.is_bid, msg.taking_order.asset_name);
            }
            this._remove_order(making_order)
        }

        // make a new trade object and sorted-ly insert it into the trades list
        const trade = {
            timestamp: msg.timestamp,
            asset_name: msg.asset_name,
            taking_order: msg.taking_order,
            making_orders: msg.making_orders,
        }
        let i;
        for (; i < this.trades.length; i++)
            if (this.trades[i].timestamp > msg.timestamp)
                break;
        this.splice('trades', i, 0, trade);

        this.dispatchEvent(new CustomEvent('confirm-trade', {detail: trade, bubbles: true, composed: true}));
    }

    // update this player's holdings when a trade occurs
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

    // handle an incoming cancel confirmation message
    _handle_confirm_cancel(msg) {
        const order = msg;
        this._remove_order(order);
        if (order.pcode == this.pcode) {
            if (order.is_bid) {
                this.availableCash += order.price * order.volume;
            }
            else {
                this._update_subproperty('availableAssets', order.asset_name, order.volume);
            }
        }

        this.dispatchEvent(new CustomEvent('confirm-order-cancel', {detail: order, bubbles: true, composed: true}));
    }

    _remove_order(order) {
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
    }

    // handle an incomming error message
    _handle_error(msg) {
        if (msg.pcode == this.pcode) {
            this.dispatchEvent(new CustomEvent('error', {detail: msg.message, bubbles: true, composed: true}));
        }
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

    _update_subproperty(property, subproperty, amount) {
        const old = this.get([property, subproperty]);
        this.set([property, subproperty], old + amount);
    }

}

window.customElements.define('trader-state', TraderState);
