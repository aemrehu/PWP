""" This module contains the resources for the product endpoints. """
import json
from flask import Response, request, url_for
from flask_restful import Resource
from jsonschema import ValidationError, validate

from flasgger import swag_from
from onlinestore import db
from onlinestore.models import Product
from onlinestore.utils import InventoryBuilder, create_error_response
from onlinestore.constants import JSON, MASON, LINK_RELATIONS_URL, PRODUCT_PROFILE


class ProductCollection(Resource):
    """ Resource ProductCollection """

    @swag_from('../../doc/product/product_collection_get.yml')
    def get(self):
        ''' Get list of all products (returns a Mason document) '''
        body = InventoryBuilder()

        body.add_namespace("store", LINK_RELATIONS_URL)
        body.add_control("self", href=url_for("api.productcollection"))
        body.add_control_all_products()  # GET
        body.add_control_add_product()  # POST

        body["products"] = []

        # List all products in the database
        for product in Product.query.all():
            item = InventoryBuilder(product.serialize())
            item.add_control("self", href=url_for("api.productitem", product=product.id))
            item.add_control("profile", PRODUCT_PROFILE)
            body["products"].append(item)

        return Response(json.dumps(body), 200, mimetype=MASON)

    @swag_from('../../doc/product/product_collection_post.yml')
    def post(self):
        ''' Create a new product '''
        if request.content_type != JSON:
            return create_error_response(
                415, "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, Product.json_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        name = request.json["name"]
        if db.session.query(Product).filter(Product.name == name).first():
            return create_error_response(
                409, "Already exists",
                f"Product with name '{name}' already exists."
            )

        product = Product()
        product.deserialize(request.json)

        db.session.add(product)
        db.session.commit()

        return Response(status=201, headers={
            "Location": url_for("api.productitem", product=product.id)
        })


class ProductItem(Resource):
    """ Resource ProductItem """

    @swag_from('../../doc/product/product_item_get.yml')
    def get(self, product):
        ''' Get product information '''
        body = InventoryBuilder(product.serialize())
        body.add_namespace("store", LINK_RELATIONS_URL)
        body.add_control("self", href=url_for("api.productitem", product=product.id))
        body.add_control("profile", PRODUCT_PROFILE)
        body.add_control("collection", href=url_for("api.productcollection"))
        body.add_control_get_productorder(product)  # GET product order for the product
        body.add_control_get_stock(product)  # GET stock for the product
        body.add_control_edit_product(product)  # PUT
        body.add_control_delete_product(product)  # DELETE

        return Response(json.dumps(body), 200, mimetype=MASON)

    @swag_from('../../doc/product/product_item_put.yml')
    def put(self, product):
        ''' Update product information '''
        if request.content_type != JSON:
            return create_error_response(
                415, "Unsupported media type",
                "Requests must be JSON"
            )

        try:
            validate(request.json, Product.json_schema())
        except ValidationError as e:
            return create_error_response(400, "Invalid JSON document", str(e))

        product.deserialize(request.json)
        db.session.add(product)
        db.session.commit()

        return Response(status=204)

    @swag_from('../../doc/product/product_item_delete.yml')
    def delete(self, product):
        ''' Delete a product '''
        db.session.delete(product)
        db.session.commit()

        return Response(status=204)
