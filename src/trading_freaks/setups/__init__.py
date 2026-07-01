"""Rule-based setup checklists."""

from trading_freaks.setups.dax_bounce import DAXBounceInput, evaluate_dax_bounce
from trading_freaks.setups.economic_data_fx import EconomicDataFXInput, evaluate_economic_data_fx
from trading_freaks.setups.fx_trendline import FXTrendlineInput, evaluate_fx_trendline
from trading_freaks.setups.premarket_high_low import (
    PremarketHighLowInput,
    evaluate_premarket_high_low,
)
from trading_freaks.setups.rectangle import RectangleInput, evaluate_rectangle
from trading_freaks.setups.us_news_breakout_checklist import (
    USNewsBreakoutInput,
    evaluate_us_news_breakout,
)
from trading_freaks.setups.us_news_reversal import USNewsReversalInput, evaluate_us_news_reversal
from trading_freaks.setups.us_reversal_without_news import (
    USReversalWithoutNewsInput,
    evaluate_us_reversal_without_news,
)

__all__ = [
    "DAXBounceInput",
    "EconomicDataFXInput",
    "FXTrendlineInput",
    "PremarketHighLowInput",
    "RectangleInput",
    "USNewsBreakoutInput",
    "USNewsReversalInput",
    "USReversalWithoutNewsInput",
    "evaluate_dax_bounce",
    "evaluate_economic_data_fx",
    "evaluate_fx_trendline",
    "evaluate_premarket_high_low",
    "evaluate_rectangle",
    "evaluate_us_news_breakout",
    "evaluate_us_news_reversal",
    "evaluate_us_reversal_without_news",
]
