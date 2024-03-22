import json
from sqlalchemy.exc import IntegrityError
from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import ValidationError, draft7_format_checker, validate
from werkzeug.exceptions import BadRequest

from onlinestore import db
from onlinestore.models import Order, Customer
from onlinestore.utils import InventoryBuilder
from onlinestore.constants import *


class OrderCollection(Resource):

    # Returns a list of orders in the database
    def get(self):
        body = InventoryBuilder()

        body.add_namespace("store", LINK_RELATIONS_URL)
        body.add_control("self", href=url_for("api.ordercollection"))
        body.add_control_all_orders()  # GET
        body.add_control_add_order()  # POST
        body["items"] = []

        for order in Order.query.all():
            item = InventoryBuilder(order.serialize())
            item.add_control("self", href=url_for("api.orderitem", order=str(order.id)))
            item.add_control("profile", ORDER_PROFILE)
            body["items"].append(item)

        return Response(json.dumps(body), 200, mimetype=MASON)

    def post(self):
        try:
            customerId = request.json["customerId"]
            if customerId is None:
                return "Request content type must be JSON", 415

            # Validate the JSON document against the schema
            try:
                validate(request.json, Order.json_schema(), format_checker=draft7_format_checker)
            except ValidationError as e:
                raise BadRequest(description=str(e))  # 400 Bad request

            if db.session.query(Customer).filter(Customer.id == customerId).first() is None:
                return f"Customer with ID {customerId} not found", 404
            try:
                order = Order()
                order.deserialize(request.json)
            except ValueError:
                return "Invalid request body", 400
            try:
                db.session.add(order)
                db.session.commit()

                order_uri = url_for("api.orderitem", id=order.id)

                return Response(status=201, headers={"Location": order_uri})
            except Exception as e:  # IntegrityError:
                db.session.rollback()
                return f"Incomplete request - missing fields - {e}", 500
        except (KeyError, ValueError):
            return "Invalid request body", 400


class OrderItem(Resource):
    def get(self, order):
        body = InventoryBuilder(order.serialize())
        body.add_namespace("store", LINK_RELATIONS_URL)
        body.add_control("self", href=url_for("api.orderitem", order=str(order.id)))
        body.add_control("profile", ORDER_PROFILE)
        body.add_control("collection", href=url_for("api.ordercollection"))
        body.add_control_customer_to_order(order)  # GET customer to order
        body.add_control_edit_order(order)  # PUT
        body.add_control_delete_order(order)  # DELETE
        
        return Response(json.dumps(body), 200, mimetype=MASON)

    def delete(self, order):
        try:
            db.session.delete(order)
            db.session.commit()

            return Response(status=204)
        except IntegrityError:
            return "Customer not found", 404

    def put(self, order):
        if not request.json:
            return "Unsupported media type", 415

        try:
            validate(request.json, Order.json_schema())
        except ValidationError as e:
            raise BadRequest(description=str(e))

        try:
            order.deserialize(request.json)
            db.session.add(order)
            try:
                db.session.commit()
            except IntegrityError:
                return "Database error", 500

            return Response(status=204)
        except IntegrityError:
            return "Customer not found", 404
