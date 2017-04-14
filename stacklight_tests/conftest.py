import logging

import pytest

from stacklight_tests import utils
logger = logging.getLogger(__name__)


def pytest_configure(config):
    config.addinivalue_line("markers",
                            "check_env(check1, check2): mark test "
                            "to run only on env, which pass all checks")


@pytest.fixture(scope="session")
def env_config():
    return utils.load_config()


@pytest.fixture(autouse=True)
def env_requirements(request, env_config):
    reserved = {'or', 'and', 'not', '(', ')'}
    marker = request.node.get_marker('check_env')
    if not marker:
        return
    marker_str = ' and '.join(marker.args)
    marker_str = marker_str.replace(
        '(', ' ( '
    ).replace(
        ')', ' ) '
    ).replace(
        '  ', ' ')
    functions = marker_str.split()
    marker_str_evalued = marker_str
    for func in functions:
        if func in reserved:
            continue
        function = globals().get(func)
        if function is None:
            logger.critical('Guard with name {} not found'.format(func))
            raise ValueError('Parse error')
        if not (func.startswith('is_') or func.startswith('has_')):
            logger.critical(
                'Guard must start with "is_" or "has_", got {} instead'.format(
                    func))
            raise ValueError('Parse error')
        marker_str_evalued = marker_str_evalued.replace(
            func, str(function(env_config)))

    if not eval(marker_str_evalued):
        pytest.skip('Requires criteria: {}, computed instead: {}'.format(
            marker_str, marker_str_evalued))


def is_fuel(env_conf):
    return env_conf.get("env", {}).get("type", "") == "fuel"


def is_mk(env_conf):
    return env_conf.get("env", {}).get("type", "") == "mk"
