import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/node_modules/@polymer/polymer/lib/elements/dom-repeat.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/redwood-period/redwood-period.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '../widgets/simple_modal.js';
import '../widgets/event_log.js';
import '../widgets/order_book.js'
import './asset_cell.js'
import './asset_table.js'

/*
    this component is the main entry point for the text interface frontend. it maintains the market state in
    the `bids`, `asks` and `trades` array properties and coordinates communication with the backend
*/

class MultipleAssetTextInterface extends PolymerElement {

    static get properties() {
        return {
            timeRemaining: Number,
            bids: Array,
            asks: Array,
            trades: Array,
            settledAssets: Object,
            availableAssets: Object,
            settledCash: Number,
            availableCash: Number,
        };
    }

    static get template() {
        return html`
            <style>
                * {
                    box-sizing: border-box;
                }
                .full-width {
                    width: 100vw;
                    margin-left: 50%;
                    transform: translateX(-50%);
                }

                .main-container {
                    width: 100%;
                    margin-top: 20px;
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: space-evenly;
                }
                .main-container > div {
                    flex: 0 0 48%;
                    margin-bottom: 20px;
                    height: 30vh;
                }

                .info-container {
                    width: 100%;
                    height: 30vh;
                    display: flex;
                    padding: 0 5px 0 5px;
                }
                .info-container > div {
                    flex: 1;
                    margin: 0 5px 0 5px;
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
            <redwood-period
                on-period-start="_start"
            ></redwood-period>
            <otree-constants
                id="constants"
            ></otree-constants>
            <order-book
                id="order_book"
                bids="{{bids}}"
                asks="{{asks}}"
                trades="{{trades}}"
                settled-assets="{{settledAssets}}"
                available-assets="{{availableAssets}}"
                settled-cash="{{settledCash}}"
                available-cash="{{availableCash}}"
            ></order-book>

            <div class="full-width">
                <div class="main-container">
                    <template is="dom-repeat" items="{{asset_names}}">
                        <div>
                            <asset-cell
                                asset-name="[[item]]"
                                bids="[[bids]]"
                                asks="[[asks]]"
                                trades="[[trades]]"
                                on-order-entered="_order_entered"
                                on-order-canceled="_order_canceled"
                                on-order-accepted="_order_accepted"
                            ></asset-cell>
                        </div>
                    </template>
                </div>
                <div class="info-container">
                    <div>
                        <asset-table
                            time-remaining="[[timeRemaining]]"
                            settled-assets="{{settledAssets}}"
                            available-assets="{{availableAssets}}"
                            settled-cash="{{settledCash}}"
                            available-cash="{{availableCash}}"
                            bids="[[bids]]"
                            asks="[[asks]]"
                        ></asset-table>
                    </div>
                    <div>
                        <event-log
                            id="log"
                            max-entries=100
                        ></event-log>
                    </div>
                </div>
            </div>
        `;
    }

    ready() {
        super.ready();

        this.pcode = this.$.constants.participantCode;
        this.asset_names = Object.keys(this.availableAssets);

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

    _order_accepted(event) {
        const order = event.detail;
        if (order.pcode == this.pcode)
            return;

        this.$.modal.modal_text = `Do you want to ${order.is_bid ? 'buy' : 'sell'} asset ${order.asset_name} for $${order.price}?`
        this.$.modal.on_close_callback = (accepted) => {
            if (!accepted)
                return;

            this.$.chan.send({
                type: 'accept_immediate',
                payload: order
            });
        };
        this.$.modal.show();
    }

    // handle an incoming trade confirmation
    _handle_confirm_trade(msg) {
        const my_trades = this.$.order_book.handle_trade(msg.making_orders, msg.taking_order, msg.asset_name, msg.timestamp);
        for (let order of my_trades) {
            this.$.log.info(`You ${order.is_bid ? 'bought' : 'sold'} asset ${order.asset_name} for $${msg.making_orders[0].price}`);
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

    _start() {
        const start_time = performance.now();
        const tick = () => {
            if (this.timeRemaining <= 0) return;
            this.timeRemaining --;
            setTimeout(tick, 1000 - (performance.now() - start_time) % 100);
        }
        setTimeout(tick, 1000);
    }
}

window.customElements.define('multiple-asset-text-interface', MultipleAssetTextInterface);
