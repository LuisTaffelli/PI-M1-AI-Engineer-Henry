"""Retry-After normalizado: sólo estados locales y segundos acotados, sin headers."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import ceil, isfinite

HTTP_RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_HTTP_ATTEMPTS = 3
MAX_HTTP_RETRY_DELAY_SECONDS = 30.0
MAX_HTTP_RETRY_WAIT_SECONDS = 60.0
GEMINI_SUITE_MAX_DELAY_SECONDS = 120.0
GEMINI_SUITE_MAX_WAIT_SECONDS = 300.0


@dataclass(frozen=True)
class RetryAfter:
    state: str = "missing"
    seconds: float | None = None
    requested_seconds: int | None = field(default=None, compare=False)
    requested_seconds_digits: int | None = field(default=None, compare=False)
    max_delay_seconds: float = field(
        default=MAX_HTTP_RETRY_DELAY_SECONDS, compare=False, repr=False
    )

    def __post_init__(self):
        if not 0 <= self.max_delay_seconds <= GEMINI_SUITE_MAX_DELAY_SECONDS:
            raise ValueError("Límite Retry-After inválido.")
        for value in (self.requested_seconds, self.requested_seconds_digits):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Diagnóstico Retry-After inválido.")
        if self.state in {"missing", "invalid"} and (
            self.requested_seconds is not None
            or self.requested_seconds_digits is not None
        ):
            raise ValueError("Diagnóstico Retry-After inesperado.")
        if self.state not in {"missing", "invalid", "valid", "too_long"}:
            raise ValueError("Estado Retry-After inválido.")
        if self.state == "valid":
            if (
                type(self.seconds) not in (int, float)
                or not 0 <= self.seconds <= self.max_delay_seconds
                or not isfinite(self.seconds)
            ):
                raise ValueError("Espera Retry-After inválida.")
        elif self.seconds is not None:
            raise ValueError("Espera Retry-After inesperada.")


def parse_retry_after(
    value: object,
    *,
    now: datetime | None = None,
    max_delay_seconds: float = MAX_HTTP_RETRY_DELAY_SECONDS,
) -> RetryAfter:
    RetryAfter(max_delay_seconds=max_delay_seconds)  # validar el límite local
    if value is None:
        return RetryAfter()
    if not isinstance(value, str):
        return RetryAfter("invalid")
    text = value.strip()
    # Conservar sólo segundos normalizados, nunca el header original. Un entero
    # patológico de más de 1.000 dígitos se diagnostica por cantidad de dígitos
    # para evitar conversiones/serializaciones numéricas sin límite.
    if text.isascii() and text.isdecimal():
        digits = text.lstrip("0") or "0"
        if len(digits) > 1000:
            return RetryAfter("too_long", requested_seconds_digits=len(digits))
        seconds = int(digits)
        if seconds > max_delay_seconds:
            return RetryAfter("too_long", requested_seconds=seconds)
        return RetryAfter(
            "valid",
            float(seconds),
            requested_seconds=seconds,
            max_delay_seconds=max_delay_seconds,
        )
    if not text or len(text) > 128:
        return RetryAfter("invalid")
    try:
        date = parsedate_to_datetime(text)
        current = now if now is not None else datetime.now(timezone.utc)
        obsolete = re.fullmatch(
            r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
            r"\d{2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)-"
            r"(\d{2}) \d{2}:\d{2}:\d{2} GMT",
            text,
        )
        if obsolete:
            # HTTP usa una ventana móvil de 50 años, no el corte fijo 1969/2068
            # del parser de correo. Un año lejano no debe parecer ya vencido.
            year = current.year + (int(obsolete.group(1)) - current.year) % 100
            date = date.replace(year=year)
            try:
                future_limit = current.replace(year=current.year + 50)
            except ValueError:  # 29 de febrero hacia un año no bisiesto.
                future_limit = current.replace(year=current.year + 50, day=28)
            if date > future_limit:
                date = date.replace(year=year - 100)
        if date.tzinfo is None:
            # HTTP admite el formato obsoleto asctime, cuya zona implícita es GMT.
            # No aceptar cualquier fecha de correo sin zona como HTTP-date.
            if not re.fullmatch(
                r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) "
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) "
                r"[ \d]\d \d{2}:\d{2}:\d{2} \d{4}",
                text,
            ):
                return RetryAfter("invalid")
            date = date.replace(tzinfo=timezone.utc)
        seconds = max(0, ceil((date - current).total_seconds()))
    except (TypeError, ValueError, OverflowError):
        return RetryAfter("invalid")
    if seconds > max_delay_seconds:
        return RetryAfter("too_long", requested_seconds=seconds)
    return RetryAfter(
        "valid",
        float(seconds),
        requested_seconds=seconds,
        max_delay_seconds=max_delay_seconds,
    )
