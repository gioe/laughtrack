from dataclasses import dataclass
from typing import Optional, Any

from laughtrack.foundation.models.types import JSONDict
from laughtrack.foundation.utilities.coercion import CoercionUtils as C


@dataclass
class TesseraCampaign:
    """Tessera campaign/ticket type data structure."""

    campaignId: str
    productId: str
    productTypeId: str
    productTypeSortOrder: int
    name: str
    description: Optional[str]
    usesSeatingChart: bool
    minimumPerOrder: Optional[int]
    maximumPerOrder: Optional[int]
    sortOrder: int
    serviceFee: float
    price: float
    doorPrice: Optional[float]
    discount: Optional[float]
    imageUrl: str
    isOnSale: bool
    isOnSaleType: str
    onSaleStartDate: Optional[str]
    onSaleEndDate: Optional[str]
    isLastCall: bool
    isSoldOut: bool
    isVisible: bool
    currentlyPasswordProtected: bool
    seatingChartUrl: str

    @staticmethod
    def from_dict(data: JSONDict) -> "TesseraCampaign":
        def _opt_int(v: Any) -> Optional[int]:
            return None if v is None or str(v).strip() == "" else C.to_int(v)

        def _opt_float(v: Any) -> Optional[float]:
            return None if v is None or str(v).strip() == "" else C.to_float(v)

        return TesseraCampaign(
            campaignId=C.str_or_default(data.get("campaignId")),
            productId=C.str_or_default(data.get("productId")),
            productTypeId=C.str_or_default(data.get("productTypeId")),
            productTypeSortOrder=C.to_int(data.get("productTypeSortOrder")),
            name=C.str_or_default(data.get("name")),
            description=C.str_or_none(data.get("description")),
            usesSeatingChart=C.to_bool(data.get("usesSeatingChart"), False),
            minimumPerOrder=_opt_int(data.get("minimumPerOrder")),
            maximumPerOrder=_opt_int(data.get("maximumPerOrder")),
            sortOrder=C.to_int(data.get("sortOrder")),
            serviceFee=C.to_float(data.get("serviceFee")),
            price=C.to_float(data.get("price")),
            doorPrice=_opt_float(data.get("doorPrice")),
            discount=_opt_float(data.get("discount")),
            imageUrl=C.str_or_default(data.get("imageUrl")),
            isOnSale=C.to_bool(data.get("isOnSale"), False),
            isOnSaleType=C.str_or_default(data.get("isOnSaleType")),
            onSaleStartDate=C.str_or_none(data.get("onSaleStartDate")),
            onSaleEndDate=C.str_or_none(data.get("onSaleEndDate")),
            isLastCall=C.to_bool(data.get("isLastCall"), False),
            isSoldOut=C.to_bool(data.get("isSoldOut"), False),
            isVisible=C.to_bool(data.get("isVisible"), True),
            currentlyPasswordProtected=C.to_bool(data.get("currentlyPasswordProtected"), False),
            seatingChartUrl=C.str_or_default(data.get("seatingChartUrl")),
        )
