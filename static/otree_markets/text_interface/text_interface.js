import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import './order_list.js';
import './trade_list.js';
import './order_enter_widget.js';
import './simple_modal.js';
import './event_log.js';

/*
    this component is the main entry point for the text interface frontend. it maintains the market state in
    the `bids`, `asks` and `trades` array properties and coordinates communication with the backend
*/

class TextInterface extends PolymerElement {

    static get properties() {
        return {
            bids: Array,
            asks: Array,
            trades: Array,
            assets: Object,
            cash: Number,
        };
    }

    static get template() {
        return html`
            <style>
                .container {
                    display: flex;
                    justify-content: space-evenly;
                }
                .container > div {
                    display: flex;
                    flex-direction: column;
                }
                .flex-fill {
                    flex: 1 0 0;
                    min-height: 0;
                }

                #main-container {
                    height: 40vh;
                    margin-bottom: 10px;
                }
                #main-container > div {
                    flex: 0 1 20%;
                }

                #log-container {
                    height: 20vh;
                }
                #log-container > div {
                    flex: 0 1 90%;
                }
            </style>

            <simple-modal
                id="modal"
            ></simple-modal>

            <redwood-channel
                id="chan"
                channel="chan"
                on-event="_on_message"
            ></redwood-channel>
            <otree-constants
                id="constants"
            ></otree-constants>

            <div class="container" id="main-container">
                <div>
                    <h3>Bids</h3>
                    <order-list
                        data-is-bid="true"
                        class="flex-fill"
                        orders="[[bids]]"
                        on-order-canceled="_order_canceled"
                    ></order-list>
                </div>
                <div>
                    <h3>Asks</h3>
                    <order-list
                        data-is-bid="false"
                        class="flex-fill"
                        orders="[[asks]]"
                        on-order-canceled="_order_canceled"
                    ></order-list>
                </div>
                <div>
                    <h3>Trades</h3>
                    <trade-list
                        class="flex-fill"
                        trades="[[trades]]"
                    ></trade-list>
                </div>
                <div>
                    <order-enter-widget
                        class="flex-fill"
                        cash="[[cash]]"
                        assets="[[assets]]"
                        on-order-entered="_order_entered"
                    ></order-enter-widget>
                </div>
            </div>
            <div class="container" id="log-container">
                <div>
                    <event-log
                        class="flex-fill"
                        id="log"
                        max-entries=100
                    ></event-log>
                </div>
            </div>
        `;
    }

    ready() {
        super.ready();
        // just a nice convenience
        this.pcode = this.$.constants.participantCode;

        // maps incoming message types to their appropriate handler
        this.message_handlers = {
            confirm_enter: this._handle_confirm_enter,
            confirm_trade: this._handle_confirm_trade,
            confirm_cancel: this._handle_confirm_cancel,
            error: this._handle_error,
        };
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
        const order = {
            timestamp: msg.timestamp,
            price: msg.price,
            volume: msg.volume,
            pcode: msg.pcode,
            asset_name: msg.asset_name,
            order_id: msg.order_id,
        };
        if (msg.is_bid)
            this._insert_bid(order);
        else
            this._insert_ask(order);
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
    }

    // insert an ask into the asks array in ascending order
    _insert_ask(order) {
        let i = 0;
        for (; i < this.asks.length; i++) {
            if (this._compare_orders(this.asks[i], order) > 0)
                break;
        }
        this.splice('asks', i, 0, order);
    }

    // triggered when this player enters an order
    // sends an order enter message to the backend
    _order_entered(event) {
        const order = event.detail;
        if (isNaN(order.price) || isNaN(order.volume)) {
            this.$.log.error('Invalid order entered');
            return;
        }
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

    // triggered when this player cancels an order
    // sends an order cancel message to the backend
    _order_canceled(event) {
        const order = event.detail;
        const is_bid = event.target.dataset.isBid == 'true';

        this.$.modal.modal_text = 'Are you sure you want to remove this order?';
        this.$.modal.on_close_callback = (accepted) => {
            if (!accepted)
                return;

            this.$.chan.send({
                type: 'cancel',
                payload: {
                    price: order.price,
                    pcode: order.pcode,
                    order_id: order.order_id,
                    asset_name: order.asset_name,
                    is_bid: is_bid,
                }
            });
        };
        this.$.modal.show();
    }

    // handle an incoming trade confirmation
    _handle_confirm_trade(msg) {
        const taking_order = msg.taking_order;
        // copy this player's cash and assets so when we change them it only triggers one update
        let new_cash   = this.cash;
        let new_assets = this.get(['assets', msg.asset_name]);
        // iterate through making orders from this trade. if a making order is yours or the taking order is yours,
        // update your cash and assets appropriately
        for (const making_order of msg.making_orders) {
            if (making_order.is_bid) {
                if (making_order.pcode == this.pcode) {
                    this.$.log.info(`You bought ${making_order.traded_volume} units of asset ${msg.asset_name}`);
                    new_cash   -= making_order.price * making_order.traded_volume;
                    new_assets += making_order.traded_volume;
                }
                if (taking_order.pcode == this.pcode) {
                    new_cash   += making_order.price * making_order.traded_volume;
                    new_assets -= making_order.traded_volume;
                }
            }
            else {
                if (making_order.pcode == this.pcode) {
                    this.$.log.info(`You sold ${making_order.traded_volume} units of asset ${msg.asset_name}`);
                    new_cash   += making_order.price * making_order.traded_volume;
                    new_assets -= making_order.traded_volume;
                }
                if (taking_order.pcode == this.pcode) {
                    new_cash   -= making_order.price * making_order.traded_volume;
                    new_assets += making_order.traded_volume;
                }
            }
            this._remove_order(making_order.order_id, making_order.is_bid)
        }
        if (taking_order.pcode == this.pcode) {
            this.$.log.info(`You ${taking_order.is_bid ? 'bought' : 'sold'} ${taking_order.traded_volume} units of asset ${msg.asset_name}`)
        }
        // only update cash/assets if necessary
        if (this.cash != new_cash) {
            this.cash = new_cash;
            this.set(['assets', msg.asset_name], new_assets);
        }
        this._remove_order(taking_order.order_id, taking_order.is_bid)

        // make a new trade object and sorted-ly insert it into the trades list
        const trade = {
            timestamp: msg.timestamp,
            asset_name: msg.asset_name,
            taking_order: taking_order,
            making_orders: msg.making_orders,
        }
        let i;
        for (; i < this.trades.length; i++)
            if (this.trades[i].timestamp > msg.timestamp)
                break;
        this.splice('trades', i, 0, trade);
    }

    // handle an incoming cancel confirmation message
    _handle_confirm_cancel(msg) {
        if (msg.pcode == this.pcode) {
            this.$.log.info(`You canceled your ${msg.is_bid ? 'bid' : 'ask'}`);
        }
        this._remove_order(msg.order_id, msg.is_bid)
    }

    // remove an order from either the bids list or the asks list
    _remove_order(order_id, is_bid) {
        const order_store_name = is_bid ? 'bids' : 'asks';
        const order_store = this.get(order_store_name);
        let i = 0;
        for (; i < order_store.length; i++)
            if (order_store[i].order_id == order_id)
                break;
        if (i >= order_store.length)
            return;
        this.splice(order_store_name, i, 1);
    }

    // handle an incomming error message
    _handle_error(msg) {
        if (msg.pcode == this.pcode) 
            this.$.log.error(msg['message'])
    }
}

window.customElements.define('text-interface', TextInterface);
