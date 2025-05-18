from safrs import ValidationError, SAFRSBase, SAFRSAPI as _SAFRSAPI
import json
import safrs
import operator

class SAFRSBase(SAFRSBase):
    """
    SAFRSBase is a subclass of SQLAlchemy's Model class, which is used to define
    database models in the SQLAlchemy ORM. It provides additional functionality
    for working with the SAFRS (SQLAlchemy Flask RESTful) framework.
    """

    __abstract__ = True

    @classmethod
    def _s_filter(cls, *filter_args, **filter_kwargs):
        """
        Apply a filter to this model
        :param filter_args: A list of filters information to apply, passed as a request URL parameter.
        Each filter object has the following fields:
        - name: The name of the field you want to filter on.
        - op: The operation you want to use (all sqlalchemy operations are available). The valid values are:
            - like: Invoke SQL like (or "ilike", "match", "notilike")
            - eq: check if field is equal to something
            - ge: check if field is greater than or equal to something
            - gt: check if field is greater than to something
            - ne: check if field is not equal to something
            - is_: check if field is a value
            - is_not: check if field is not a value
            - le: check if field is less than or equal to something
            - lt: check if field is less than to something
        - val: The value that you want to compare.
        :return: sqla query object
        """
        try:
            filters = json.loads(filter_args[0])
        except json.decoder.JSONDecodeError:
            raise ValidationError("Invalid filter format (see https://github.com/thomaxxl/safrs/wiki)")

        if not isinstance(filters, list):
            filters = [filters]

        expressions = []
        query = cls._s_query

        for filt in filters:
            if not isinstance(filt, dict):
                safrs.log.warning(f"Invalid filter '{filt}'")
                continue
            attr_name = filt.get("name")
            attr_val = filt.get("val")
            if attr_name != "id" and attr_name not in cls._s_jsonapi_attrs:
                raise ValidationError(f'Invalid filter "{filt}", unknown attribute "{attr_name}"')

            op_name = filt.get("op", "").strip("_")
            attr = cls._s_jsonapi_attrs[attr_name] if attr_name != "id" else cls.id
            if op_name in ["in", "notin"]:
                op = getattr(attr, op_name + "_")
                query = query.filter(op(attr_val))
            elif op_name in ["like", "ilike", "match", "notilike"] and hasattr(attr, "like"):
                # => attr is Column or InstrumentedAttribute
                like = getattr(attr, op_name)
                expressions.append(like(attr_val))
            elif not hasattr(operator, op_name):
                raise ValidationError(f'Invalid filter "{filt}", unknown operator "{op_name}"')
            else:
                op = getattr(operator, op_name)
                expressions.append(op(attr, attr_val))

        return query.filter(operator.and_(*expressions))
