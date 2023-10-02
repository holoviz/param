import asyncio

import param
import pytest

param.parameterized.warnings_as_exceptions = True

def async_execute(func):
    event_loop = asyncio.get_running_loop()
    if event_loop.is_running():
        asyncio.create_task(func())
    else:
        event_loop.run_until_complete(func())
    return

@pytest.fixture
def dataframe():
    import pandas as pd
    return pd.DataFrame({
        'int': [1, 2, 3],
        'float': [3.14, 6.28, 9.42],
        'str': ['A', 'B', 'C']
    }, index=[1, 2, 3], columns=['int', 'float', 'str'])

@pytest.fixture
def async_executor():
    old_executor = param.parameterized.async_executor
    param.parameterized.async_executor = async_execute
    yield
    param.parameterized.async_executor = old_executor
