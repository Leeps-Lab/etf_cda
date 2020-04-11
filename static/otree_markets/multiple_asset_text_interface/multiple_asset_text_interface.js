import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '../widgets/simple_modal.js';
import '../widgets/event_log.js';
import '../widgets/order_book.js'
import './asset_cell.js'

/*
    this component is the main entry point for the text interface frontend. it maintains the market state in
    the `bids`, `asks` and `trades` array properties and coordinates communication with the backend
*/

class MultipleAssetTextInterface extends PolymerElement {

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
                .full-width {
                    width: 100vw;
                    margin-left: 50%;
                    transform: translateX(-50%);
                }
                .container {
                    width: 100%;
                    margin-top: 20px;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-evenly;
                }
                .container > div {
                    flex: 0 0 48%;
                    margin-bottom: 20px;
                    height: 30vh;
                    border: 1px solid black;
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
            <order-book
                id="order_book"
                bids="{{bids}}"
                asks="{{asks}}"
                trades="{{trades}}"
                assets="{{assets}}"
                cash="{{cash}}"
            ></order-book>

            <div class="full-width">
                <div class="container">
                    <template is="dom-repeat" items="{{asset_names}}">
                        <div>
                            <asset-cell
                                asset-name="[[item]]"
                                bids="[[bids]]"
                                asks="[[asks]]"
                                trades="[[trades]]"
                                on-order-entered="_order_entered"
                                on-order-canceled="_order_canceled"
                            ></asset-cell>
                        </div>
                    </template>
                </div>
                <event-log
                    id="log"
                    max-entries=100
                ></event-log>
            </div>
        `;
    }

    ready() {
        super.ready();

        this.pcode = this.$.constants.participantCode;
        this.asset_names = Object.keys(this.assets);

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
        const order = msg;
        this.$.order_book.insert_order(order);
    }

    // triggered when this player enters an order
    // sends an order enter message to the backend
    _order_entered(event) {
        const order = event.detail;
        if (isNaN(order.price)) {
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

        this.$.modal.modal_text = 'Are you sure you want to remove this order?';
        this.$.modal.on_close_callback = (accepted) => {
            if (!accepted)
                return;

            this.$.chan.send({
                type: 'cancel',
                payload: order
            });
        };
        this.$.modal.show();
    }

    // handle an incoming trade confirmation
    _handle_confirm_trade(msg) {
        const my_trades = this.$.order_book.handle_trade(msg.making_orders, msg.taking_order, msg.asset_name, msg.timestamp);
        for (let order of my_trades) {
            this.$.log.info(`You ${order.is_bid ? 'bought' : 'sold'} ${order.traded_volume} ${order.traded_volume == 1 ? 'unit' : 'units'} of asset ${order.asset_name}`);
        }
    }

    // handle an incoming cancel confirmation message
    _handle_confirm_cancel(msg) {
        const order = msg;
        this.$.order_book.remove_order(order);
        if (order.pcode == this.pcode) {
            this.$.log.info(`You canceled your ${msg.is_bid ? 'bid' : 'ask'}`);
        }
    }

    // handle an incomming error message
    _handle_error(msg) {
        if (msg.pcode == this.pcode) 
            this.$.log.error(msg['message'])
    }
}

window.customElements.define('multiple-asset-text-interface', MultipleAssetTextInterface);
