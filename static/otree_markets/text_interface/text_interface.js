import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import './order_list.js';
import './order_enter_widget.js';

class TextInterface extends PolymerElement {

    static get properties() {
        return {
            bids: Array,
            asks: Array,
            assets: Object,
            cash: Number,
        };
    }

    static get template() {
        return html`
            <style>
                #order-container {
                    width: 100%;
                    height: 40vh;
                    display: flex;
                    justify-content: space-evenly;
                }
                #order-container > div {
                    flex: 0 1 20%;
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                }
                .flex-fill-vertical {
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

            <div id="order-container">
                <div>
                    <h3>Bids</h3>
                    <order-list
                        class="flex-fill-vertical"
                        orders="[[bids]]"
                    ></order-list>
                </div>
                <div>
                    <h3>Asks</h3>
                    <order-list
                        class="flex-fill-vertical"
                        orders="[[asks]]"
                    ></order-list>
                </div>
                <div>
                    <order-enter-widget
                        cash="[[cash]]"
                        assets="[[assets]]"
                        class="flex-fill-vertical"
                        on-order-entered="_order_entered"
                    ></order-enter-widget>
                </div>
            </div>
        `;
    }

    ready() {
        super.ready();

        this.message_handlers = {
            confirm_enter: this._handle_confirm_enter,
        };
        console.log(this.bids);
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

}

window.customElements.define('text-interface', TextInterface);
