"""Pure calculations. Unknown costs never become zero implicitly."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, ROUND_CEILING
import math


class ValidationError(ValueError):
    pass


def number(data, key, minimum=0, maximum=None):
    value = data.get(key)
    if value is None or value == "" or isinstance(value, bool):
        raise ValidationError(f"Eksik veya geçersiz alan: {key}")
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValidationError(f"Geçersiz sayı: {key}")
    if not result.is_finite() or result < minimum or (maximum is not None and result > maximum):
        raise ValidationError(f"Aralık dışında: {key}")
    return result


def text(data, key, limit=500, required=True):
    value = data.get(key, "")
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise ValidationError(f"Geçersiz metin: {key}")
    return value.strip()


def money(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def pricing(data):
    """One variation/order, one currency. All percentages use explicit bases."""
    text(data, "variation", 500)
    if text(data, "supplier").casefold() != "printmarkt":
        raise ValidationError("Bu pilot yalnızca Printmarkt maliyetlerini kabul eder.")
    currency = text(data, "currency", 3).upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValidationError("Üç harfli para birimi gerekli.")
    text(data, "source", 1000)
    text(data, "source_date", 10)
    from datetime import date
    try:
        source_date = date.fromisoformat(data["source_date"])
    except ValueError:
        raise ValidationError("Kaynak tarihi YYYY-MM-DD olmalı.")
    if source_date > date.today():
        raise ValidationError("Kaynak tarihi gelecekte olamaz.")
    cost_keys = ("production", "bulk_shipping", "domestic_shipping", "customs_tax", "other_costs", "listing_fee", "payment_fixed", "ads_fixed")
    costs = {key: number(data, key) for key in cost_keys}
    price = number(data, "price", Decimal("0.01"))
    shipping = number(data, "shipping_charged")
    buyer_tax = number(data, "buyer_tax")
    discount = number(data, "discount_pct", maximum=100) / 100
    transaction_rate = number(data, "transaction_pct", maximum=100) / 100
    payment_rate = number(data, "payment_pct", maximum=100) / 100
    ads_rate = number(data, "ads_pct", maximum=100) / 100
    target = number(data, "target_margin_pct", maximum=99) / 100
    for key in ("payment_on_tax", "transaction_on_tax", "ads_on_tax"):
        if not isinstance(data.get(key), bool):
            raise ValidationError(f"Ücret matrahı seçilmeli: {key}")
    revenue = price * (1 - discount) + shipping
    transaction = (revenue + (buyer_tax if data["transaction_on_tax"] else 0)) * transaction_rate
    payment = (revenue + (buyer_tax if data["payment_on_tax"] else 0)) * payment_rate
    ads = (revenue + (buyer_tax if data["ads_on_tax"] else 0)) * ads_rate
    total_cost = sum(costs.values()) + transaction + payment + ads
    profit = revenue - total_cost
    rate_sum = transaction_rate + payment_rate + ads_rate
    tax_fees = buyer_tax * sum(rate for key, rate in (("transaction_on_tax", transaction_rate), ("payment_on_tax", payment_rate), ("ads_on_tax", ads_rate)) if data[key])
    denominator = 1 - rate_sum - target
    target_price = None
    if denominator > 0 and discount < 1:
        raw_target = max(Decimal(0), ((sum(costs.values()) + tax_fees) / denominator - shipping) / (1 - discount))
        target_price = float(raw_target.quantize(Decimal("0.01"), rounding=ROUND_CEILING))
    age = (date.today() - source_date).days
    return {"currency": currency, "evidence": "estimate", "source_age_days": age, "stale": age > 30,
            "revenue": money(revenue), "total_cost": money(total_cost), "profit": money(profit),
            "margin_pct": money(profit / revenue * 100) if revenue else None,
            "transaction_fee": money(transaction), "payment_fee": money(payment), "ads_fee": money(ads),
            "target_price": target_price,
            "note": "Kullanıcı girdileriyle senaryo; Printmarkt veya Etsy üzerinden doğrulanmadı. Vergi tahsilatı gelir sayılmaz. Sabit giderler siparişe ayrılan tutarlardır."}


def quality(data):
    kind = text(data, "kind", 20)
    ratios = {"seamless_source": [(1, 1)], "mural_source": [(3, 2)], "seamless_mockup": [(1, 1), (3, 4)], "mural_mockup": [(4, 3)]}
    if kind not in ratios:
        raise ValidationError("Bilinmeyen görsel türü.")
    width, height = number(data, "width_px", 1), number(data, "height_px", 1)
    if width != int(width) or height != int(height):
        raise ValidationError("Piksel boyutları tam sayı olmalı.")
    width_cm, height_cm = number(data, "width_cm", Decimal("0.01")), number(data, "height_cm", Decimal("0.01"))
    required_w = math.ceil(width_cm / Decimal("2.54") * 300)
    required_h = math.ceil(height_cm / Decimal("2.54") * 300)
    dpi = min(width * Decimal("2.54") / width_cm, height * Decimal("2.54") / height_cm)
    ratio_ok = any(width * y == height * x for x, y in ratios[kind])
    return {"required_width_px": required_w, "required_height_px": required_h,
            "effective_dpi": money(dpi), "resolution_ok": width >= required_w and height >= required_h,
            "ratio_ok": ratio_ok, "print_ready": False, "input_evidence": "manual",
            "note": "Elle girilen ölçüler değerlendirildi. Dosya incelenmedi; netlik, renk, 3×3 tekrar, kenar birleşimi ve tedarikçi payları ayrıca doğrulanmalı. Seamless için ölçü, tek repeat'in fiziksel baskı ölçüsüdür; toplam duvar değildir."}
