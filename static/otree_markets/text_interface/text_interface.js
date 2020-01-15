import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import './order_list.js';
import './order_enter_widget.js';

class TextInterface extends PolymerElement {

    static get properties() {
        return {
            _bids: {
                type: Array,
                value: function () { return []; },
            },
            _asks: {
                type: Array,
                value: function () { return []; },
            },
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
                        orders="[[_bids]]"
                    ></order-list>
                </div>
                <div>
                    <h3>Asks</h3>
                    <order-list
                        class="flex-fill-vertical"
                        orders="[[_asks]]"
                    ></order-list>
                </div>
                <div>
                    <order-enter-widget
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

    _insert_bid(order) {
        let i = 0;
        for (; i < this._bids.length; i++) {
            if (this._bids[i].price < order.price)
                break;
        }
        this.splice('_bids', i, 0, order);
    }

    _insert_ask(order) {
        let i = 0;
        for (; i < this._asks.length; i++) {
            if (this._asks[i].price > order.price)
                break;
        }
        this.splice('_asks', i, 0, order);
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
