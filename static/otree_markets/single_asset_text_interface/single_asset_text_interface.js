import { html, PolymerElement } from '/static/otree-redwood/node_modules/@polymer/polymer/polymer-element.js';
import '/static/otree-redwood/src/redwood-channel/redwood-channel.js';
import '/static/otree-redwood/src/otree-constants/otree-constants.js';
import '../widgets/order_list.js';
import '../widgets/trade_list.js';
import './order_enter_widget.js';
import '../widgets/simple_modal.js';
import '../widgets/event_log.js';
import '../widgets/order_book.js'

/*
    this component is the main entry point for the text interface frontend. it maintains the market state in
    the `bids`, `asks` and `trades` array properties and coordinates communication with the backend
*/

class SingleAssetTextInterface extends PolymerElement {

    static get properties() {
        return {
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

            <div class="container" id="main-container">
                <div>
                    <h3>Bids</h3>
                    <order-list
                        class="flex-fill"
                        orders="[[bids]]"
                        on-order-canceled="_order_canceled"
                        on-order-accepted="_order_accepted"
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
                    <h3>Asks</h3>
                    <order-list
                        class="flex-fill"
                        orders="[[asks]]"
                        on-order-canceled="_order_canceled"
                        on-order-accepted="_order_accepted"
                    ></order-list>
                </div>
                <div>
                    <order-enter-widget
                        class="flex-fill"
                        settled-assets="{{settledAssets}}"
                        available-assets="{{availableAssets}}"
                        settled-cash="{{settledCash}}"
                        available-cash="{{availableCash}}"
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
        const order = msg;
        this.$.order_book.insert_order(order);
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

        this.$.modal.modal_text = 'Are you sure you want to remove this order?';
        this.$.modal.on_close_callback = (accepted) => {
            if (!accepted)
                return;

            this.$.chan.send({
                type: 'cancel',
                payload: order,
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

window.customElements.define('single-asset-text-interface', SingleAssetTextInterface);
