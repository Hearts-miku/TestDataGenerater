"""Faker rule engine — semantic field-name inference + typed value generation."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from faker import Faker


# ── Rule descriptor ───────────────────────────────────────────────────────────

@dataclass
class Rule:
    tag: str
    min_val: Optional[int] = None
    max_val: Optional[int] = None
    max_chars: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    enum_values: Optional[list[str]] = None
    nullable: bool = False
    null_rate: float = 0.05


# ── Semantic field-name patterns ──────────────────────────────────────────────
#  (field_name_pattern, type_category_pattern, rule_tag)
_RULES: list[tuple[re.Pattern, Optional[str], str]] = [
    # email
    (re.compile(r"email",              re.I), None,        "email"),
    # phone
    (re.compile(r"phone|mobile|tel",   re.I), None,        "phone"),
    # username
    (re.compile(r"username|user_name|login|account", re.I), None, "username"),
    # name parts
    (re.compile(r"first.?name|fname|given.?name",    re.I), None, "first_name"),
    (re.compile(r"last.?name|lname|surname|family",  re.I), None, "last_name"),
    (re.compile(r"^(full.?name|name)$",              re.I), None, "name"),
    # location
    (re.compile(r"city",               re.I), None,        "city"),
    (re.compile(r"country",            re.I), None,        "country"),
    (re.compile(r"state|province|region", re.I), None,     "state"),
    (re.compile(r"zip|postal",         re.I), None,        "postcode"),
    # web — ip_address must come BEFORE the generic address pattern
    (re.compile(r"url|website|homepage|site", re.I), None, "url"),
    (re.compile(r"ip.?addr|ip_address|ip$",   re.I), None, "ipv4"),
    (re.compile(r"address|street",     re.I), None,        "address"),
    (re.compile(r"uuid|guid",                 re.I), None, "uuid4"),
    (re.compile(r"sku",                       re.I), None, "sku"),
    # company / job
    (re.compile(r"company|corp|org",          re.I), None, "company"),
    (re.compile(r"job|position|occupation|title", re.I), None, "job"),
    # content / text
    (re.compile(r"bio|description|about|summary|content|body|remark|comment|note", re.I), None, "text"),
    (re.compile(r"headline|subject",          re.I), None, "sentence"),
    # time — must check type_category too to avoid matching string fields
    (re.compile(r"birth.?date|dob",           re.I), "date",     "date_of_birth"),
    (re.compile(r"date|_at$|_date$",          re.I), "date",     "date_of_birth"),
    (re.compile(r"_at$|time",                 re.I), "datetime", "datetime"),
    (re.compile(r"date",                      re.I), "datetime", "datetime"),
    # numeric semantic
    (re.compile(r"price|cost|fee",            re.I), "decimal",  "price"),
    (re.compile(r"amount|total|revenue|salary|income", re.I), "decimal", "decimal"),
    (re.compile(r"age$",                      re.I), "integer",  "random_int"),
    (re.compile(r"quantity|qty|count$|num$",  re.I), "integer",  "random_int"),
    # boolean
    (re.compile(r"^is_|^has_|^can_|active|enabled|deleted|verified", re.I), "boolean", "boolean"),
    # color / misc
    (re.compile(r"color|colour",              re.I), None,        "color"),
    (re.compile(r"lat|latitude",              re.I), None,        "latitude"),
    (re.compile(r"lon|lng|longitude",         re.I), None,        "longitude"),
    (re.compile(r"avatar|photo|image|img",    re.I), None,        "image_url"),
]

# Type-category fallbacks when no semantic pattern matches
_TYPE_FALLBACKS: dict[str, str] = {
    "integer":  "random_int",
    "float":    "pyfloat",
    "decimal":  "decimal",
    "string":   "pystr",
    "text":     "text",
    "boolean":  "boolean",
    "date":     "date_of_birth",
    "datetime": "datetime",
    "json":     "json",
    "enum":     "enum",
    "unknown":  "word",
}


class FakerRuleEngine:
    def __init__(self, locale: str = "en_US") -> None:
        self._faker = Faker(locale)
        Faker.seed(0)

    def infer_rule(self, field_name: str, type_category: str) -> Rule:
        for pattern, type_filter, tag in _RULES:
            if pattern.search(field_name):
                if type_filter is None or type_filter == type_category:
                    return Rule(tag=tag)
        # Fallback to type-based tag
        tag = _TYPE_FALLBACKS.get(type_category, "word")
        return Rule(tag=tag)

    def generate(self, rule: Rule) -> Any:
        if rule.nullable and random.random() < rule.null_rate:
            return None
        return _generate_by_rule(self._faker, rule)

    def generate_batch(self, rule: Rule, n: int, unique: bool = False) -> list[Any]:
        if not unique:
            return [self.generate(rule) for _ in range(n)]

        # Unique generation with exhaustion detection
        seen: set = set()
        results: list[Any] = []
        max_attempts = n * 50
        attempts = 0

        while len(results) < n and attempts < max_attempts:
            val = _generate_by_rule(self._faker, rule)
            attempts += 1
            if val not in seen:
                seen.add(val)
                results.append(val)

        if len(results) < n:
            raise ValueError(
                f"Cannot generate {n} unique values for rule tag={rule.tag!r} "
                f"(only {len(results)} possible after {max_attempts} attempts)"
            )
        return results


def _generate_by_rule(f: Faker, rule: Rule) -> Any:
    match rule.tag:
        case "email":         return f.email()
        case "phone":         return f.phone_number()
        case "username":      return f.user_name()
        case "first_name":    return f.first_name()
        case "last_name":     return f.last_name()
        case "name":          return f.name()
        case "city":          return f.city()
        case "country":       return f.country()
        case "state":         return f.state()
        case "address":       return f.address()
        case "postcode":      return f.postcode()
        case "url":           return f.url()
        case "ipv4":          return f.ipv4()
        case "uuid4":         return f.uuid4()
        case "sku":           return f.bothify(text="??-####").upper()
        case "company":       return f.company()
        case "job":           return f.job()
        case "text":          return f.text(max_nb_chars=200)
        case "sentence":      return f.sentence()
        case "word":          return f.word()
        case "date_of_birth": return f.date_of_birth().isoformat()
        case "datetime":      return f.date_time().isoformat(sep=" ")
        case "boolean":       return f.boolean()
        case "color":         return f.color_name()
        case "latitude":      return float(f.latitude())
        case "longitude":     return float(f.longitude())
        case "image_url":     return f.image_url()
        case "json":          return "{}"
        case "random_int":
            lo = rule.min_val if rule.min_val is not None else 1
            hi = rule.max_val if rule.max_val is not None else 2_147_483_647
            return random.randint(lo, hi)
        case "price":
            return round(random.uniform(0.01, 9999.99), 2)
        case "decimal":
            p = rule.precision or 10
            s = rule.scale or 2
            return round(random.uniform(0, 10 ** (p - s) - 0.01), s)
        case "pyfloat":       return round(f.pyfloat(positive=True), 4)
        case "pystr":
            max_c = rule.max_chars or 50
            return f.pystr(max_chars=max_c)
        case "enum":
            if rule.enum_values:
                return random.choice(rule.enum_values)
            return f.word()
        case _:               return f.word()
