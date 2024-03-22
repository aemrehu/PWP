from flask import url_for
from werkzeug.routing import BaseConverter
from werkzeug.exceptions import NotFound, Conflict, BadRequest, UnsupportedMediaType

from onlinestore.models import *
from onlinestore.constants import *


class MasonBuilder(dict):
    """
    A convenience class for managing dictionaries that represent Mason
    objects. It provides nice shorthands for inserting some of the more
    elements into the object but mostly is just a parent for the much more
    useful subclass defined next. This class is generic in the sense that it
    does not contain any application specific implementation details.
    """

    def add_error(self, title, details):
        """
        Adds an error element to the object. Should only be used for the root
        object, and only in error scenarios.

        Note: Mason allows more than one string in the @messages property (it's
        in fact an array). However we are being lazy and supporting just one
        message.

        : param str title: Short title for the error
        : param str details: Longer human-readable description
        """

        self["@error"] = {
            "@message": title,
            "@messages": [details],
        }

    def add_namespace(self, ns, uri):
        """
        Adds a namespace element to the object. A namespace defines where our
        link relations are coming from. The URI can be an address where
        developers can find information about our link relations.

        : param str ns: the namespace prefix
        : param str uri: the identifier URI of the namespace
        """

        if "@namespaces" not in self:
            self["@namespaces"] = {}

        self["@namespaces"][ns] = {
            "name": uri
        }

    def add_control(self, ctrl_name, href, **kwargs):
        """
        Adds a control property to an object. Also adds the @controls property
        if it doesn't exist on the object yet. Technically only certain
        properties are allowed for kwargs but again we're being lazy and don't
        perform any checking.

        The allowed properties can be found from here
        https://github.com/JornWildt/Mason/blob/master/Documentation/Mason-draft-2.md

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        """

        if "@controls" not in self:
            self["@controls"] = {}

        self["@controls"][ctrl_name] = kwargs
        self["@controls"][ctrl_name]["href"] = href

    def add_control_post(self, ctrl_name, title, href, schema):
        """
        Utility method for adding POST type controls. The control is
        constructed from the method's parameters. Method and encoding are
        fixed to "POST" and "json" respectively.

        : param str ctrl_name: name of the control (including namespace if any)
        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """

        self.add_control(
            ctrl_name,
            href,
            method="POST",
            encoding="json",
            title=title,
            schema=schema
        )

    def add_control_put(self, title, href, schema):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control name, method and
        encoding are fixed to "edit", "PUT" and "json" respectively.

        : param str href: target URI for the control
        : param str title: human-readable title for the control
        : param dict schema: a dictionary representing a valid JSON schema
        """

        self.add_control(
            "edit",
            href,
            method="PUT",
            encoding="json",
            title=title,
            schema=schema
        )

    def add_control_delete(self, title, href):
        """
        Utility method for adding PUT type controls. The control is
        constructed from the method's parameters. Control method is fixed to
        "DELETE", and control's name is read from the class attribute
        *DELETE_RELATION* which needs to be overridden by the child class.

        : param str href: target URI for the control
        : param str title: human-readable title for the control
        """

        self.add_control(
            "storage:delete",
            href,
            method="DELETE",
            title=title,
        )


class InventoryBuilder(MasonBuilder):
    def add_control_all_products(self):
        self.add_control(
            "store:products-all",
            url_for("api.productcollection"),
            method="GET",
            title="Get all products",
        )

    def add_control_delete_product(self, product):
        self.add_control(
            "store:delete",
            url_for("api.productitem", name=product.name),
            method="DELETE",
            title="Delete a product"
        )

    def add_control_add_product(self):
        self.add_control(
            "store:add-product",
            url_for("api.productcollection"),
            method="POST",
            title="Add a new product",
            encoding="json",
            schema=Product.json_schema()
        )

    def add_control_edit_product(self, product):
        self.add_control(
            "edit",
            url_for("api.productitem", name=product.name),
            method="PUT",
            title="Edit a product",
            encoding="json",
            schema=Product.json_schema()
        )


class ProductConverter(BaseConverter):
    def to_python(self, product_name):  # used in routing
        db_product = Product.query.filter_by(name=product_name).first()
        if db_product is None:
            raise NotFound
        return db_product

    def to_url(self, db_product):  # used in reverse routing
        # db_product.name
        # AttributeError: 'str' object has no attribute 'name'
        return db_product


class CustomerConverter(BaseConverter):
    def to_python(self, customer_uuid):  # used in routing
        db_customer = Customer.query.filter_by(uuid=customer_uuid).first()
        if db_customer is None:
            raise NotFound
        return db_customer

    def to_url(self, db_customer):  # used in reverse routing
        return db_customer.uuid


class OrderConverter(BaseConverter):
    def to_python(self, order_id):  # used in routing
        db_order = Order.query.filter_by(id=order_id).first()
        if db_order is None:
            raise NotFound
        return db_order

    def to_url(self, db_order):  # used in reverse routing
        return db_order.id


class ProductOrderConverter(BaseConverter):
    def to_python(self, productOrder_id):  # used in routing
        db_product_order = ProductOrder.query.filter_by(id=productOrder_id).first()
        if db_product_order is None:
            raise NotFound
        return db_product_order

    def to_url(self, db_product_order):  # used in reverse routing
        return db_product_order.id


class StockConverter(BaseConverter):
    def to_python(self, productId):  # used in routing
        db_stock = Stock.query.filter_by(productId=productId).first()
        if db_stock is None:
            raise NotFound
        return db_stock

    def to_url(self, db_stock):  # used in reverse routing
        return db_stock.productId
