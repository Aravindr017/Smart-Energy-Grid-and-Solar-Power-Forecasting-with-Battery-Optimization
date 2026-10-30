"""Shared INR tariff and illustrative battery-cost assumptions."""

CURRENCY_CODE = "INR"
CURRENCY_SYMBOL = "₹"

OFF_PEAK_RATE_INR_PER_KWH = 5.30
NORMAL_RATE_INR_PER_KWH = 6.70
PEAK_RATE_INR_PER_KWH = 7.30
EXPORT_FEEDIN_RATE_INR_PER_KWH = 0.0

OFF_PEAK_HOURS = (22, 23, 0, 1, 2, 3, 4, 5)
NORMAL_HOURS = (10, 11, 12, 13, 14, 15, 16, 17)
PEAK_HOURS = (6, 7, 8, 9, 18, 19, 20, 21)

BATTERY_DEGRADATION_COST_INR_PER_KWH = 0.50
BATTERY_INSTALLED_COST_INR_PER_KWH = 15000.0


def get_tariff_config():
    """Return JSON-serializable tariff and financial assumptions for clients."""
    return {
        "currency_code": CURRENCY_CODE,
        "currency_symbol": CURRENCY_SYMBOL,
        "unit": f"{CURRENCY_SYMBOL}/kWh",
        "tariff_rates": {
            "off_peak_rate": OFF_PEAK_RATE_INR_PER_KWH,
            "normal_rate": NORMAL_RATE_INR_PER_KWH,
            "peak_rate": PEAK_RATE_INR_PER_KWH,
            "export_feedin_rate": EXPORT_FEEDIN_RATE_INR_PER_KWH,
        },
        "tariff_hours": {
            "off_peak": list(OFF_PEAK_HOURS),
            "normal": list(NORMAL_HOURS),
            "peak": list(PEAK_HOURS),
        },
        "financial_assumptions": {
            "degradation_cost_per_kwh": BATTERY_DEGRADATION_COST_INR_PER_KWH,
            "installed_cost_per_kwh": BATTERY_INSTALLED_COST_INR_PER_KWH,
        },
        "disclaimer": "Financial results are estimates based on simulated tariff assumptions, not actual utility bills or guaranteed savings.",
    }
