from flask_rest_jsonapi.data_layers.base import BaseDataLayer
from flask_rest_jsonapi.exceptions import ObjectNotFound

from app.api.helpers.exceptions import UnprocessableEntity, ConflictException
from app.api.helpers.ticketing import TicketingManager
from app.models.order import Order


class ChargesLayer(BaseDataLayer):

    def create_object(self, data, view_kwargs):
        """
        create_object method for the Charges layer
        charge the user using paypal or stripe
        :param data:
        :param view_kwargs:
        :return:
        """

        if view_kwargs.get('order_identifier').isdigit():
            # when id is passed
            order = Order.query.filter_by(id=view_kwargs['order_identifier']).first()
        else:
            # when identifier is passed
            order = Order.query.filter_by(identifier=view_kwargs['order_identifier']).first()

        if not order:
            raise ObjectNotFound({'parameter': 'order_identifier'},
                                 "Order with identifier: {} not found".format(view_kwargs['order_identifier']))
        elif order.status == 'cancelled' or order.status == 'expired' or order.status == 'completed':
            raise ConflictException({'parameter': 'id'},
                                    "You cannot charge payments on a cancelled, expired or completed order")
        elif (not order.amount) or order.amount == 0:
            raise ConflictException({'parameter': 'id'},
                                    "You cannot charge payments on a free order")

        data['id'] = order.id

        # charge through stripe
        if order.payment_mode == 'stripe':
            if not data.get('stripe'):
                raise UnprocessableEntity({'source': ''}, "stripe token is missing")
            if not order.event.can_pay_by_stripe:
                raise ConflictException({'': ''}, "This event doesn't accept payments by Stripe")
            try:
                success, response = TicketingManager.charge_stripe_order_payment(order, data['stripe'])
                data['status'] = success
                data['message'] = response
            except Exception:
                data['status'] = False
                data['message'] = "Stripe hasn't been configured properly."

        # charge through paypal
        elif order.payment_mode == 'paypal':
            if not data.get('paypal'):
                raise UnprocessableEntity({'source': ''}, "paypal token is missing")
            if not order.event.can_pay_by_paypal:
                raise ConflictException({'': ''}, "This event doesn't accept payments by Paypal")
            try:
                success, response = TicketingManager.charge_paypal_order_payment(order, data['paypal'])
                data['status'] = success
                data['message'] = response
            except Exception:
                data['status'] = False
                data['message'] = "Paypal hasn't been configured properly."

        return data
