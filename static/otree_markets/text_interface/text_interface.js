import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import './order_list.js';
import './trade_list.js';
import './order_enter_widget.js';

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
                #container {
                    width: 100%;
                    height: 40vh;
                    display: flex;
                    justify-content: space-evenly;
                }
                #container > div {
                    flex: 0 1 20%;
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                }
                .flex-fill {
                    flex: 1 0 auto;
                }
            </style>

            <redwood-channel
                id="chan"
                channel="chan"
                on-event="_on_message"
            ></redwood-channel>
            <otree-constants
                id="constants"
            ></otree-constants>

            <div id="container">
                <div>
                    <h3>Bids</h3>
                    <order-list
                        class="flex-fill"
                        orders="[[bids]]"
                    ></order-list>
                </div>
                <div>
                    <h3>Asks</h3>
                    <order-list
                        class="flex-fill"
                        orders="[[asks]]"
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
        `;
    }

    ready() {
        super.ready();

        // maps incoming message types to their appropriate handler
        this.message_handlers = {
            confirm_enter: this._handle_confirm_enter,
            confirm_trade: this._handle_confirm_trade,
        };
    }

    _on_message(event) {
        const msg = event.detail.payload;
        const handler = this.message_handlers[msg.type];
        if (!handler) {
            throw `error: invalid message type: ${msg.type}`;
        }
        handler.call(this, msg.payload);
    }

    _handle_confirm_enter(msg) {
        const order = {
            timestamp: msg.timestamp,
            price: msg.price,
            pcode: msg.pcode,
            asset_name: msg.asset_name,
            order_id: msg.order_id,
        };
        if (msg.is_bid)
            this._insert_bid(order);
        else
            this._insert_ask(order);
    }

    _compare_orders(o1, o2) {
        // compare two order objects. sort first by price, then by timestamp
        // return a positive or negative number a la c strcmp
        if (o1.price == o2.price)
            return o1.timestamp - o2.timestamp;
        else
            return o1.price - o2.price;
    }

    _insert_bid(order) {
        let i = 0;
        for (; i < this.bids.length; i++) {
            if (this._compare_orders(this.bids[i].price, order.price) < 0)
                break;
        }
        this.splice('bids', i, 0, order);
    }

    _insert_ask(order) {
        let i = 0;
        for (; i < this.asks.length; i++) {
            if (this._compare_orders(this.asks[i].price, order.price) > 0)
                break;
        }
        this.splice('asks', i, 0, order);
    }

    _order_entered(event) {
        this.$.chan.send({
            type: 'enter',
            payload: {
                price: event.detail.price,
                is_bid: event.detail.is_bid,
                pcode: this.$.constants.participantCode,
                asset_name: "A",
            }
        });
    }

    _handle_confirm_trade(msg) {
        if (msg.bid_pcode == this.$.constants.participantCode) {
            this.cash -= msg.price;
            this.assets[msg.asset_name]++;
        }
        if (msg.ask_pcode == this.$.constants.participantCode) {
            this.cash += msg.price;
            this.assets[msg.asset_name]--;
        }
        this._remove_order(msg.bid_order_id, true);
        this._remove_order(msg.ask_order_id, false);

        const trade = {
            timestamp: msg.timestamp,
            price: msg.price,
            bid_pcode: msg.bid_pcode,
            ask_pcode: msg.ask_pcode,
        }
        let i;
        for (; i < this.trades.length; i++)
            if (this.trades[i].timestamp > msg.timestamp)
                break;
        this.splice('trades', i, 0, trade);
    }

    _remove_order(order_id, is_bid) {
        const order_store_name = is_bid ? 'bids' : 'asks';
        const order_store = this.get(order_store_name);
        let i = 0;
        for (; i < order_store; i++)
            if (order_store[i].order_id == order_id)
                break;
        if (i >= order_store.length)
            return;
        this.splice(order_store_name, i, 1);
    }

}

window.customElements.define('text-interface', TextInterface);
