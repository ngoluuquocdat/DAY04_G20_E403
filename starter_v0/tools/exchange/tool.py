def get_exchange_rate(base: str = "USD", target: str = "VND") -> str:
    """
    Mock function to get exchange rates for standard pairs.
    """
    base = base.upper()
    target = target.upper()
    
    # Mock data for some common pairs
    mock_rates = {
        ("USD", "VND"): 25400,
        ("EUR", "VND"): 27500,
        ("USD", "EUR"): 0.92,
        ("EUR", "USD"): 1.08,
        ("VND", "USD"): 0.000039,
    }
    
    rate = mock_rates.get((base, target))
    
    if rate is not None:
        return f"1 {base} = {rate} {target} (Mocked Data)"
    
    return f"Exchange rate for {base} to {target} is not available in mock data."
