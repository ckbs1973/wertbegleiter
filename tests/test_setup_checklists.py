import sys
import unittest
from datetime import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from trading_freaks.models import Direction
from trading_freaks.risk.position_sizing import calculate_risk_plan
from trading_freaks.setups.dax_bounce import DAXBounceInput, evaluate_dax_bounce
from trading_freaks.setups.economic_data_fx import EconomicDataFXInput, evaluate_economic_data_fx
from trading_freaks.setups.fx_trendline import FXTrendlineInput, evaluate_fx_trendline
from trading_freaks.setups.premarket_high_low import PremarketHighLowInput, evaluate_premarket_high_low
from trading_freaks.setups.rectangle import RectangleInput, evaluate_rectangle
from trading_freaks.setups.us_news_reversal import USNewsReversalInput, evaluate_us_news_reversal
from trading_freaks.setups.us_reversal_without_news import (
    USReversalWithoutNewsInput,
    evaluate_us_reversal_without_news,
)


def valid_long_risk():
    return calculate_risk_plan(
        account_equity=10_000,
        risk_percent=1.0,
        direction=Direction.LONG,
        entry=100.0,
        stop_loss=99.0,
        take_profit=101.0,
    )


class SetupChecklistTests(unittest.TestCase):
    def test_economic_data_fx_passes_and_blocks_pre_event_position(self):
        candidate = EconomicDataFXInput(
            pair="EURUSD",
            direction=Direction.LONG,
            event_type="cpi",
            weekly_calendar_checked=True,
            is_g8_g10_pair=True,
            no_position_before_event=True,
            pairs_selected_15m_before=True,
            support_resistance_marked=True,
            data_checked_after_release=True,
            surprise_is_large=True,
            data_is_unified=True,
            momentum_pips=25,
            no_simultaneous_buy_sell_stops=True,
            current_spread_pips=1,
            planned_target_pips=25,
        )

        self.assertTrue(evaluate_economic_data_fx(candidate, risk_plan=valid_long_risk()).trade_allowed)
        blocked = evaluate_economic_data_fx(
            EconomicDataFXInput(**{**candidate.__dict__, "no_position_before_event": False}),
            risk_plan=valid_long_risk(),
        )
        self.assertFalse(blocked.trade_allowed)
        self.assertIn("Keine Position vor Eventeroeffnung", blocked.failed_conditions)

    def test_rectangle_passes_and_blocks_non_rectangle_pattern(self):
        candidate = RectangleInput(
            symbol="EXAMPLE",
            direction=Direction.LONG,
            daily_volume=2_000_000,
            is_penny_stock=False,
            has_m1_intraday_gaps=False,
            prior_move_is_momentum=True,
            correction_fraction_of_momentum=0.25,
            correction_candles=7,
            is_horizontal_range=True,
            is_flag_or_triangle=False,
            rectangle_clear=True,
            upper_touches=3,
            lower_touches=2,
            entry_near_rectangle_edge=True,
            exit_at_crv_one_or_trailing_allowed=True,
        )

        self.assertTrue(evaluate_rectangle(candidate, risk_plan=valid_long_risk()).trade_allowed)
        blocked = evaluate_rectangle(
            RectangleInput(**{**candidate.__dict__, "is_flag_or_triangle": True}),
            risk_plan=valid_long_risk(),
        )
        self.assertFalse(blocked.trade_allowed)
        self.assertIn("Keine Flagge oder Dreieck", blocked.failed_conditions)

    def test_other_named_setups_have_valid_information_only_paths(self):
        risk = valid_long_risk()
        checks = [
            evaluate_us_news_reversal(
                USNewsReversalInput(
                    symbol="EXAMPLE",
                    direction=Direction.LONG,
                    daily_volume=2_000_000,
                    has_news_or_data=True,
                    gap_percent=4,
                    m1_chart_available=True,
                    initial_move_against_news_or_extreme_mixed_move=True,
                    far_from_vwap=True,
                    bottom_or_top_formed=True,
                    entry_signal_present=True,
                    target_is_vwap_or_technical_level=True,
                    room_to_target_for_min_crv=True,
                    movement_is_orderly_enough=True,
                    entry_not_based_on_hope=True,
                    close_by_end_of_day_planned=True,
                ),
                risk_plan=risk,
            ),
            evaluate_us_reversal_without_news(
                USReversalWithoutNewsInput(
                    symbol="EXAMPLE",
                    direction=Direction.LONG,
                    current_time=time(16, 30),
                    daily_volume=2_000_000,
                    has_relevant_news=False,
                    has_strong_volume_news_hint=False,
                    traded_once_today=False,
                    far_from_vwap=True,
                    fibonacci_drawn=True,
                    vwap_beyond_50_retracement=True,
                    ema9_signal_close=True,
                    follow_through_candle=True,
                    room_to_382_retracement=True,
                    take_profit_at_50_or_vwap=True,
                    close_by_2159_planned=True,
                    long_short_balance_ok=True,
                ),
                risk_plan=risk,
            ),
            evaluate_premarket_high_low(
                PremarketHighLowInput(
                    symbol="EXAMPLE",
                    direction=Direction.LONG,
                    has_news_catalyst=True,
                    premarket_trend_in_breakout_direction=True,
                    gap_percent=4,
                    strong_opening_drive=True,
                    high_liquidity=True,
                    m1_clean_after_1430=True,
                    premarket_level_formed_by_1525=True,
                    consolidation_after_level=True,
                    no_premarket_trade_taken=True,
                    entry_near_breakout_level=True,
                    optional_hold_check_passed=True,
                    close_intraday_planned=True,
                ),
                risk_plan=risk,
            ),
            evaluate_fx_trendline(
                FXTrendlineInput(
                    pair="EURUSD",
                    direction=Direction.LONG,
                    daily_g8_g10_screening_done=True,
                    timeframe_h4_or_higher=True,
                    trendline_touches_before_trade=2,
                    trade_at_third_touch=True,
                    market_is_calm=True,
                    sentiment_not_extreme_against_trade=True,
                    no_risk_event_today=True,
                    no_fresh_currency_news=True,
                    order_planned_5_to_10_pips_before_line=True,
                    order_type_matches_direction=True,
                    spread_cost_ok=True,
                    delete_open_limit_before_2300=True,
                    daytrade_close_before_day_end=True,
                ),
                risk_plan=risk,
            ),
            evaluate_dax_bounce(
                DAXBounceInput(
                    symbol="DAX",
                    direction=Direction.LONG,
                    is_dax_or_supported_index_commodity=True,
                    purely_technical_no_news=True,
                    h4_d1_w1_zones_identified=True,
                    zone_strength_confirmed=True,
                    economic_calendar_checked=True,
                    no_nearby_risk_event=True,
                    order_10_to_15_points_before_zone=True,
                    limit_order_allowed_by_plan=True,
                    target_points_planned=50,
                    crv_minimum_possible=True,
                    screenshots_planned=True,
                ),
                risk_plan=risk,
            ),
        ]

        self.assertTrue(all(result.trade_allowed for result in checks))
        self.assertTrue(all(result.information_only for result in checks))


if __name__ == "__main__":
    unittest.main()

