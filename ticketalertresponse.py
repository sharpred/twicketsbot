from dataclasses import dataclass
from typing import Any, List, TypeVar, Callable, Type, cast


T = TypeVar("T")

def from_bool(x: Any) -> bool | None:
    if isinstance(x, bool):
        return x
    if x is None:
        return None  # Allow None values
    if isinstance(x, str):
        return x.lower() == "true"  # Convert string "true"/"false" to bool
    if isinstance(x, int):
        return bool(x)  # Convert 0/1 to False/True
    raise ValueError(f"Cannot convert {x} to boolean")



def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class Price:
    id: str | None  # Allow id to be either a string or None
    currency_code: str
    label: str
    face_value: int
    original_fee: int
    net_fee: int
    net_selling_price: int

    @staticmethod
    def from_dict(obj: Any) -> 'Price':
        assert isinstance(obj, dict)
        id = obj.get("id")  # Accept whatever is in JSON
        currency_code = from_str(obj.get("currencyCode"))
        label = from_str(obj.get("label"))
        face_value = from_int(obj.get("faceValue"))
        original_fee = from_int(obj.get("originalFee"))
        net_fee = from_int(obj.get("netFee"))
        net_selling_price = from_int(obj.get("netSellingPrice"))
        return Price(id, currency_code, label, face_value, original_fee, net_fee, net_selling_price)

    def to_dict(self) -> dict:
        result: dict = {}
        result["id"] = self.id  # Just store the value without forcing None
        result["currencyCode"] = from_str(self.currency_code)
        result["label"] = from_str(self.label)
        result["faceValue"] = from_int(self.face_value)
        result["originalFee"] = from_int(self.original_fee)
        result["netFee"] = from_int(self.net_fee)
        result["netSellingPrice"] = from_int(self.net_selling_price)
        return result


@dataclass
class Pricing:
    options: str
    prices: List[Price]

    @property
    def number_of_tickets(self) -> int:
        """Returns the total number of tickets in the pricing list."""
        return len(self.prices)

    @property
    def required_single_ticket(self) -> bool:
        """
        Checks if the first ticket has a label of 'Adult Weekend Ticket' or 
        'Weekend Campervan Pass' and if there is exactly one ticket.
        """
        if self.number_of_tickets == 1 and self.prices:
            first_label = self.prices[0].label
            return first_label in {"Adult Weekend Ticket", "Weekend Campervan Pass"}
        return False

    @staticmethod
    def from_dict(obj: Any) -> 'Pricing':
        assert isinstance(obj, dict)
        options = from_str(obj.get("options"))
        prices = from_list(Price.from_dict, obj.get("prices"))
        return Pricing(options, prices)

    def to_dict(self) -> dict:
        result: dict = {}
        result["options"] = from_str(self.options)
        result["prices"] = from_list(lambda x: to_class(Price, x), self.prices)
        return result


@dataclass
class ResponseDatum:
    type: str
    area: str
    section: str
    row: str
    id: str
    pricing: Pricing
    common_attributes: List[int]
    individual_attributes: List[List[int]]
    splits: List[int]
    delivery_method_types: List[str]
    seller_will_consider_offers: bool
    segment_id: str

    @property
    def single_ticket(self) -> bool:
        """Returns True if only a single ticket is available, otherwise False."""
        return self.pricing.number_of_tickets == 1

    @property
    def is_required_ticket(self) -> bool:
        """Returns True if this is a single ticket and has a special label."""
        return self.pricing.required_single_ticket

    @staticmethod
    def from_dict(obj: Any) -> 'ResponseDatum':
        assert isinstance(obj, dict)
        type = from_str(obj.get("type"))
        area = from_str(obj.get("area"))
        section = from_str(obj.get("section"))
        row = from_str(obj.get("row"))
        id = from_str(obj.get("id"))
        pricing = Pricing.from_dict(obj.get("pricing"))
        common_attributes = from_list(from_int, obj.get("commonAttributes"))
        individual_attributes = from_list(lambda x: from_list(from_int, x), obj.get("individualAttributes"))
        splits = from_list(from_int, obj.get("splits"))
        delivery_method_types = from_list(from_str, obj.get("deliveryMethodTypes"))
        seller_will_consider_offers = from_bool(obj.get("sellerWillConsiderOffers")) or False
        segment_id = from_str(obj.get("segmentId"))
        return ResponseDatum(type, area, section, row, id, pricing, common_attributes, individual_attributes, splits, delivery_method_types, seller_will_consider_offers, segment_id)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = from_str(self.type)
        result["area"] = from_str(self.area)
        result["section"] = from_str(self.section)
        result["row"] = from_str(self.row)
        result["id"] = from_str(self.id)
        result["pricing"] = to_class(Pricing, self.pricing)
        result["commonAttributes"] = from_list(from_int, self.common_attributes)
        result["individualAttributes"] = from_list(lambda x: from_list(from_int, x), self.individual_attributes)
        result["splits"] = from_list(from_int, self.splits)
        result["deliveryMethodTypes"] = from_list(from_str, self.delivery_method_types)
        result["sellerWillConsiderOffers"] = from_bool(self.seller_will_consider_offers)
        result["segmentId"] = from_str(self.segment_id)
        return result

    @property
    def url_id(self) -> str:
        """Extracts the part after '@' in the id field if present."""
        return self.id.split('@')[1] if '@' in self.id else ''

@dataclass
class TicketAlertResponse:
    response_data: List[ResponseDatum]
    response_code: int
    description: str
    clock: str

    @property
    def has_valid_tickets(self) -> bool:
        """Returns True if at least one ResponseDatum has is_required_ticket == True."""
        return any(item.is_required_ticket for item in self.response_data)

    @staticmethod
    def from_dict(obj: Any) -> 'TicketAlertResponse':
        assert isinstance(obj, dict)
        response_data = from_list(ResponseDatum.from_dict, obj.get("responseData"))
        response_code = from_int(obj.get("responseCode"))
        description = from_str(obj.get("description"))
        clock = from_str(obj.get("clock"))
        return TicketAlertResponse(response_data, response_code, description, clock)

    def to_dict(self) -> dict:
        result: dict = {}
        result["responseData"] = from_list(lambda x: to_class(ResponseDatum, x), self.response_data)
        result["responseCode"] = from_int(self.response_code)
        result["description"] = from_str(self.description)
        result["clock"] = from_str(self.clock)
        return result


def ticket_alert_response_from_dict(s: Any) -> TicketAlertResponse:
    return TicketAlertResponse.from_dict(s)


def ticket_alert_response_to_dict(x: TicketAlertResponse) -> Any:
    return to_class(TicketAlertResponse, x)
