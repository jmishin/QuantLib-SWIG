import logging
import QuantLib as ql

# Настройка сквозного логирования в консоль
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("QuantLibBondPricing")


def setup_market_data(today: ql.Date, calendar: ql.Calendar, day_counter: ql.DayCounter) -> ql.Sofr:
    """Создает прогнозную кривую и наполняет индекс SOFR историческими фиксациями."""
    logger.info("Инициализация рыночных данных и кривой прогнозирования...")
    
    # Создаем плоскую форвардную кривую (ставка 5%)
    flat_forward = ql.FlatForward(today, 0.05, day_counter)
    forecasting_curve = ql.YieldTermStructureHandle(flat_forward)
    sofr_index = ql.Sofr(forecasting_curve)

    # Наполнение истории для обеспечения lookback (с середины мая)
    start_date_historic = ql.Date(15, 5, 2026)
    d = start_date_historic
    fixings_count = 0
    
    while d < today:
        if calendar.isBusinessDay(d):
            sofr_index.addFixing(d, 0.045)  # Историческая ставка 4.5%
            fixings_count += 1
        d = calendar.advance(d, 1, ql.Days)
        
    logger.info(f"Добавлено {fixings_count} исторических фиксаций в индекс SOFR.")
    return sofr_index


def create_lookback_bond(issue_date: ql.Date, maturity_date: ql.Date, 
                         calendar: ql.Calendar, day_counter: ql.DayCounter, 
                         sofr_index: ql.Sofr) -> ql.Bond:
    """Генерирует Leg с конвенцией Simple Average и конструирует объект Bond."""
    logger.info("Генерация расписания выплат и ручная сборка купонного Leg...")
    
    schedule = ql.Schedule(
        issue_date, maturity_date, ql.Period(6, ql.Months), calendar,
        ql.ModifiedFollowing, ql.ModifiedFollowing,
        ql.DateGeneration.Forward, False
    )

    nominal = 1000.0
    gearing = 1.0
    spread = 0.0075  # Спред 75 bps
    custom_leg = ql.Leg()

    for i in range(len(schedule) - 1):
        cp = ql.OvernightIndexedCoupon(
            schedule[i + 1], nominal, schedule[i], schedule[i + 1],
            sofr_index, gearing, spread,
            ql.Date(), ql.Date(), day_counter, False,
            ql.RateAveraging.Simple
        )
        custom_leg.append(cp)

    settlement_days = 2
    # Используем стандартный конструктор базового класса Bond
    bond = ql.Bond(settlement_days, ql.Russia(), issue_date, custom_leg)
    logger.info(f"Облигация успешно создана. Количество купонов: {len(schedule) - 1}.")
    return bond


def calculate_zspread_brent(bond: ql.Bond, base_curve: ql.YieldTermStructureHandle, 
                            market_clean_price: float) -> float:
    """Рассчитывает Z-спред флоатера методом Brent через ZeroSpreadedTermStructure."""
    logger.info(f"Запуск численного решателя Brent для поиска Z-спреда при цене {market_clean_price}...")
    
    spread_quote = ql.SimpleQuote(0.0)
    spread_handle = ql.QuoteHandle(spread_quote)
    
    # Строим spreaded-структуру (рыночный стандарт SimpleThenCompounded + Semiannual)
    spreaded_curve = ql.ZeroSpreadedTermStructure(
        base_curve, spread_handle, ql.SimpleThenCompounded, ql.Semiannual
    )
    
    spreaded_engine = ql.DiscountingBondEngine(ql.YieldTermStructureHandle(spreaded_curve))
    bond.setPricingEngine(spreaded_engine)

    # Целевая функция невязки для Brent: (Текущая чистая цена - Рыночная чистая цена)
    def objective_function(s: float) -> float:
        spread_quote.setValue(s)
        return bond.cleanPrice() - market_clean_price

    solver = ql.Brent()
    accuracy = 1e-6
    guess = 0.0050  # Стартовое предположение: 50 bps
    step = 0.0001   # Шаг: 1 bp

    # Решаем уравнение objective_function(s) = 0
    z_spread = solver.solve(objective_function, accuracy, guess, step)
    return z_spread


def main():
    try:
        # 1. Тайм-контекст (текущая дата — внутри первого купона)
        today = ql.Date(17, 6, 2026)
        ql.Settings.instance().evaluationDate = today
        logger.info(f"Установлена системная дата оценки QuantLib: {today.ISO()}")

        calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
        day_counter = ql.Actual360()

        # 2. Подготовка окружения
        sofr_index = setup_market_data(today, calendar, day_counter)
        my_lookback_bond = create_lookback_bond(ql.Date(1, 6, 2026), ql.Date(1, 6, 2028), 
                                                calendar, day_counter, sofr_index)

        # 3. Интеграция кастомного lookback-прайсера из SWIG
        logger.info("Подключение кастомного прайсера ArithmeticAveragedLookbackOvernightIndexedCouponPricer (5 дней)...")
        my_pricer = ql.ArithmeticAveragedLookbackOvernightIndexedCouponPricer(5)
        ql.setCouponPricer(my_lookback_bond.cashflows(), my_pricer)

        # 4. Первичная теоретическая оценка стоимости
        base_curve_handle = sofr_index.forwardingTermStructure()
        standard_engine = ql.DiscountingBondEngine(base_curve_handle)
        my_lookback_bond.setPricingEngine(standard_engine)

        logger.info("--- Теоретические метрики (без спреда) ---")
        logger.info(f"Теоретическая грязная цена (NPV): {my_lookback_bond.NPV():.6f}")
        logger.info(f"Накопленный купонный доход (Accrued): {my_lookback_bond.accruedAmount(today):.6f}")
        logger.info(f"Теоретическая чистая цена (Clean): {my_lookback_bond.cleanPrice():.6f}")

        # Логирование прогнозных ставок по купонам
        for cf in my_lookback_bond.cashflows():
            c = ql.as_overnight_indexed_coupon(cf)
            if c:
                logger.info(f" Прогноз купона {c.date().ISO()}: {c.rate() * 100:.4f}%")

        # 5. Анализ рыночных метрик относительно рыночной котировки
        market_clean_price = 101.0
        logger.info("--- Анализ рыночных метрик ---")

        # А. Расчет Yield

        bond_price = ql.BondPrice(float(market_clean_price), ql.BondPrice.Clean)

        # 2. Передаем объект структуры первым аргументом
        bond_yield = my_lookback_bond.bondYield(
            bond_price, 
            day_counter, 
            ql.Compounded, 
            ql.Semiannual, 
            today
        )
        
        logger.info(f"Yield to Maturity (при чистой цене {market_clean_price}): {bond_yield * 100:.4f}%")

        # Б. Расчет Z-Спреда через Brent
        z_spread = calculate_zspread_brent(my_lookback_bond, base_curve_handle, market_clean_price)
        logger.info(f"Z-Spread (через Brent Solver): {z_spread * 10000.0:.4f} bps")

    except Exception as e:
        logger.critical(f"Критическая ошибка выполнения скрипта: {str(e)}", exc_info=True)


if __name__ == "__main__":
    main()

